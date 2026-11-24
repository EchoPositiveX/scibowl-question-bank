"""Extract raw question records from one NSB round PDF.

Ported from the old `nsb` repo's `src/parse_pdf.py` (NSBParser) with the same
line-grouping and regex logic, so results match the old parser. Differences:

- Fixes for bad PDFs come from corrections.yaml instead of a hard-coded list.
- Paths are passed in explicitly instead of being read from the current directory.
- Image cropping is optional (it is the slow part), and images go to a folder you choose.
- The output is a list of `RawQuestion` records; `convert.py` turns them into the
  published question format.

Layout fixes since the port (QB-07, QB-08, QB-28) are described in docs/decisions.md.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from PIL import Image

from .corrections import Corrections, apply_extract_corrections

log = logging.getLogger(__name__)

QUESTION_NUMBER_CHOICES = [r"\d+"]
SUBJECT_CHOICES = ["Mathematics", "Math", "Life Science", "Energy", "Physical Science", r"[A-Z\s]+"]
QUESTION_TYPE_CHOICES = ["Short Answer", "Multiple Choice"]


def _group(choices: list[str]) -> str:
    return f"({'|'.join(choices)})"


_NUM = _group(QUESTION_NUMBER_CHOICES)
_SUBJ = _group(SUBJECT_CHOICES)
_TYPE = _group(QUESTION_TYPE_CHOICES)

DEFAULT_QUESTION_REGEX = re.compile(rf"\*?{_NUM}\)\s+{_SUBJ}\s+{_TYPE}\s+(.*)", re.IGNORECASE)
SUBJECT_ONLY_REGEX = re.compile(rf"\*?{_NUM}\)\s+{_SUBJ}\s+(.*)", re.IGNORECASE)
MISSING_SUBJECT_REGEX = re.compile(rf"\*?{_NUM}\)\s+{_TYPE}\s+(.*)", re.IGNORECASE)
# A choice line. The text can be empty when the choice is a formula drawn as a picture.
CHOICE_REGEX = re.compile(r"([WXYZ])\)(?:\s+(.*)|\s*$)", re.IGNORECASE)
NEW_QUESTION_REGEX = re.compile(r"\d+\)\s+")
# Page footers ("Round 14 Page 9", "Middle School Regional NSB® PAGE 3") and separator rows.
FOOTER_REGEX = re.compile(r"\bpage\s*\d+\s*$|^Middle School - Round \d+[A-Z]?$", re.IGNORECASE)
# The moderator's closing script printed after the last bonus (2022 rounds).
ROUND_END_REGEX = re.compile(r"^Before we leave\b", re.IGNORECASE)
SEPARATOR_REGEX = re.compile(r"^\s*[~_=*-]{5,}\s*$")
# "ANSWER:", "ANSWER :", "Answer:", and "ANSWER 212" (colon left out).
ANSWER_REGEX = re.compile(r"^(?:ANSWER\b\s*:?|(?i:answer)\s*:)\s*")

# Rounds whose file names don't contain their round number.
SPECIAL_ROUND_NUMBERS = {
    "de1_for_web": 20,
    "de3_for_web": 21,
    "rr2_for_web": 18,
    "rr5_for_web": 19,
}


def parse_round_number(round_name: str) -> int | None:
    """Round number from a file name like 'Round-10C-MS' or '2019-NSB-MSR-Round-1A'."""
    if not round_name:
        return None
    if round_name in SPECIAL_ROUND_NUMBERS:
        return SPECIAL_ROUND_NUMBERS[round_name]
    cleaned = re.sub(r"\b(2016|2019|2020|2021|2022)\b", "", round_name.lower())
    match = re.search(r"\d+", cleaned)
    return int(match.group()) if match else None


@dataclass
class RawQuestion:
    """One toss-up or bonus as found in the PDF, before cleanup."""

    level: str
    set: str
    round: str
    pdf: str  # relative to data/raw, forward slashes
    page: int
    number: int
    part: str  # "tossup" or "bonus"
    subject_raw: str
    style: str  # "Short Answer" or "Multiple Choice"
    question_lines: list[str]
    choices: dict[str, str] | None
    answer_lines: list[str]
    raw_pdf_lines: list[str]
    images: dict[str, str | None] = field(default_factory=lambda: {"question": None, "answer": None, "entire": None})
    overrides_applied: list[str] = field(default_factory=list)
    # True when some question text reaches into the ANSWER row, so it may hold part of the answer.
    answer_row_overlap: bool = False
    # Where a fraction or root bar (a short rule with characters just above and below it) is printed:
    # "question" and/or "answer". Its text comes apart in the PDF, so the question needs review.
    stacked_fractions: list[str] = field(default_factory=list)

    @property
    def round_number(self) -> int | None:
        return parse_round_number(self.round)


def _same_line(a: dict, b: dict) -> bool:
    return abs(a["top"] - b["top"]) <= 0.5 and abs(a["size"] - b["size"]) <= 0.1


def _x_adjacent(left: dict, right: dict) -> bool:
    return -1 <= right["x0"] - left["x1"] <= 2


def normalize_chars(chars: list[dict]) -> list[dict]:
    """Fix two kinds of small raised or lowered characters before words are built (QB-32).

    - Subscripts (C6H12O6, NH3) sit more than 3 points below the line's top, so pdfplumber
      puts them on a line of their own and they end up as loose numbers at the end of the
      text. A run of small characters whose bottom lines up with a larger neighbour's is
      moved onto that neighbour's line.
    - A small raised "o" right after a digit is a degree sign typed as a superscript letter
      ("100oC"), and becomes "°".
    """
    out = [dict(c) for c in chars]
    moved = None  # (last moved run's last char as it was, shift), to carry the shift on to "(l" + ")"
    i = 0
    while i < len(out):
        j = i + 1
        while j < len(out) and _same_line(out[j], out[i]) and _x_adjacent(out[j - 1], out[j]):
            j += 1
        run = out[i:j]
        small = run[0].get("size", 0)
        if moved and abs(moved[0]["top"] - run[0]["top"]) <= 1 and _x_adjacent(moved[0], run[0]):
            for c in run:
                c["top"] += moved[1]
                c["doctop"] += moved[1]
                c["bottom"] += moved[1]
            moved = (dict(chars[j - 1]), moved[1])
            i = j
            continue
        moved = None
        for nb, left in ((out[i - 1] if i > 0 else None, True), (out[j] if j < len(out) else None, False)):
            if nb is None or not nb["text"].strip() or nb.get("size", 0) < small * 1.2:
                continue
            adjacent = _x_adjacent(nb, run[0]) if left else _x_adjacent(run[-1], nb)
            if not adjacent:
                continue
            if abs(run[0]["bottom"] - nb["bottom"]) <= 2.5 and 3 < run[0]["top"] - nb["top"] <= 8:
                shift = nb["top"] - run[0]["top"]
                for c in run:
                    c["top"] += shift
                    c["doctop"] += shift
                    c["bottom"] += shift
                moved = (dict(chars[j - 1]), shift)
                break
            if (left and len(run) == 1 and run[0]["text"] == "o" and nb["text"].isdigit()
                    and run[0]["bottom"] < nb["bottom"] - 2):
                run[0]["text"] = "°"
                break
        i = j
    return out


def group_words_into_lines(words: list[dict], y_tolerance: float = 3) -> list[dict]:
    """Group pdfplumber words into text lines with bounding boxes (same logic as the old parser)."""
    lines: list[dict] = []
    current: list[dict] = []
    current_y = None

    def finalize(wlist: list[dict]) -> dict | None:
        if not wlist:
            return None
        ordered = sorted(wlist, key=lambda w: w["x0"])
        parts = []
        for i, w in enumerate(ordered):
            if i > 0 and w["x0"] - ordered[i - 1]["x1"] > 1:
                parts.append(" ")
            parts.append(w["text"])
        text = re.sub(r"\s+", " ", "".join(parts)).strip()
        text = re.sub(r"\*?(\d+)\)\s*", r"\1) ", text)
        return {
            "text": text,
            "x0": min(w["x0"] for w in wlist),
            "x1": max(w["x1"] for w in wlist),
            "y0": min(w["top"] for w in wlist),
            "y1": max(w["bottom"] for w in wlist),
        }

    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if not current:
            current, current_y = [w], w["top"]
        elif abs(w["top"] - current_y) <= y_tolerance:
            current.append(w)
        else:
            line = finalize(current)
            if line:
                lines.append(line)
            current, current_y = [w], w["top"]
    line = finalize(current)
    if line:
        lines.append(line)
    return lines


class _Box:
    def __init__(self, line: dict | None = None):
        self.x0 = self.y0 = float("inf")
        self.x1 = self.y1 = 0.0
        if line:
            self.add(line)

    def add(self, line: dict) -> None:
        self.x0 = min(self.x0, line["x0"])
        self.x1 = max(self.x1, line["x1"])
        self.y0 = min(self.y0, line["y0"])
        self.y1 = max(self.y1, line["y1"])


def find_fraction_bars(page) -> list[tuple[float, float, float]]:
    """(x0, x1, y) of each fraction or root bar on a page: a short horizontal rule with printed
    characters just above and just below it, as in 1 over 3 or the top of a square root."""
    chars = [c for c in page.chars if c["text"].strip()]
    bars = []
    for r in page.lines + page.rects:
        if r["bottom"] - r["top"] >= 2 or not 3 < r["x1"] - r["x0"] < 80:
            continue
        over = [c for c in chars if c["x0"] >= r["x0"] - 2 and c["x1"] <= r["x1"] + 2]
        if (any(0 < r["top"] - c["bottom"] < 6 for c in over)
                and any(0 < c["top"] - r["bottom"] < 6 for c in over)):
            bars.append((r["x0"], r["x1"], (r["top"] + r["bottom"]) / 2))
    return bars


def _has_bar(bars: list[tuple[float, float, float]], box: "_Box", y1: float | None = None) -> bool:
    bottom = box.y1 if y1 is None else y1
    return any(box.y0 - 6 <= y <= bottom + 6 and x1 >= box.x0 and x0 <= box.x1 for x0, x1, y in bars)


def _is_header(text: str) -> str | None:
    upper = text.upper()
    if "TOSS-UP" in upper:
        return "tossup"
    if "BONUS" in upper:
        return "bonus"
    return None


# Subject labels printed in the PDFs, longest first so "Earth Science" wins over "Earth".
KNOWN_SUBJECTS = [
    "Earth and Space Science", "Earth & Space", "Earth and Space", "Earth Science", "General Science",
    "Physical Science", "Life Science", "Mathematics", "Chemistry", "Biology", "Physics", "Energy", "Math",
]
# A known subject, followed by a non-letter, the end of the line, or a style glued on ("ENERGYMultiple Choice").
KNOWN_SUBJECT_REGEX = re.compile(
    rf"({'|'.join(re.escape(s) for s in KNOWN_SUBJECTS)})(?=[^A-Za-z]|$|{_TYPE})", re.IGNORECASE
)
STYLE_AT_START = re.compile(rf"^[\s.:–—-]*{_TYPE}\s*:?\s*", re.IGNORECASE)
QUESTION_NUMBER_REGEX = re.compile(rf"\*?{_NUM}\)\s+(.*)")
# An unknown "subject" this long is really question text (the PDF printed no subject).
MAX_UNKNOWN_SUBJECT_WORDS = 2


def _split_style(text: str) -> tuple[str | None, str]:
    """Take a leading "Short Answer" / "Multiple Choice" (with any dash or dot before it) off the text."""
    m = STYLE_AT_START.match(text)
    if m:
        return m.group(1), text[m.end():]
    return None, text


def _match_question_line(text: str):
    """Return (number, subject, style, rest) if this line starts a question, else None.

    style is None when the line doesn't print one; the caller guesses it.
    """
    m = QUESTION_NUMBER_REGEX.match(text)
    if not m:
        return None
    num, after = m.groups()

    known = KNOWN_SUBJECT_REGEX.match(after)
    if known:
        subj = known.group(1)
        rest = after[known.end():]
        # "Math Math ..." : the subject printed twice.
        again = re.match(rf"\s*{re.escape(subj)}(?=[^A-Za-z]|$)", rest, re.IGNORECASE)
        if again:
            rest = rest[again.end():]
        style, rest = _split_style(rest)
        return num, subj, style, rest.lstrip(" .:–—-")

    # Fall back to the old parser's patterns for labels we don't know.
    for regex in (DEFAULT_QUESTION_REGEX, MISSING_SUBJECT_REGEX, SUBJECT_ONLY_REGEX):
        m = regex.match(text)
        if not m:
            continue
        if regex is DEFAULT_QUESTION_REGEX:
            num, subj, style, rest = m.groups()
        elif regex is MISSING_SUBJECT_REGEX:
            (num, style, rest), subj = m.groups(), ""
        else:
            (num, subj, rest), style = m.groups(), None
            found_style, rest_after = _split_style(rest)
            if found_style:
                style, rest = found_style, rest_after
        if len(subj.split()) > MAX_UNKNOWN_SUBJECT_WORDS:
            # Question words swallowed as a subject: give them back.
            return num, "", None, after
        return num, subj, style, rest
    return None


def _is_prose(text: str) -> bool:
    """True if the text has at least two real words (not just numbers or variables)."""
    return len(re.findall(r"[A-Za-z]{3,}", text)) >= 2


def _is_footer(text: str) -> bool:
    """Page footers and separator rows, which belong to no question."""
    return (len(text) <= 90 and bool(FOOTER_REGEX.search(text))) or bool(SEPARATOR_REGEX.match(text))


def _starts_new_question(text: str) -> bool:
    """True for a "N) SUBJECT ..." line. Numbered statements inside a question ("1) a square is ...") are not."""
    if not NEW_QUESTION_REGEX.match(text):
        return False
    found = _match_question_line(text)
    return bool(found and (found[2] or KNOWN_SUBJECT_REGEX.match(found[1])))


def _next_answer_top(lines: list[dict], i: int) -> float | None:
    """Top of the ANSWER line that ends the question starting at lines[i], if there is one."""
    while i < len(lines):
        text = lines[i]["text"]
        if ANSWER_REGEX.match(text):
            return lines[i]["y0"]
        if _starts_new_question(text) or _is_header(text) or ROUND_END_REGEX.match(text):
            return None
        i += 1
    return None


# How far (in points) a line may reach into the ANSWER row and still count as question text.
ANSWER_ROW_TOLERANCE = 1.0


def _guess_style(text: str) -> str:
    return "Multiple Choice" if "which of the following" in text.lower() else "Short Answer"


def extract_round(
    pdf_path: Path,
    raw_root: Path,
    images_dir: Path | None = None,
    resolution: int = 300,
    corrections: Corrections | None = None,
) -> list[RawQuestion]:
    """Extract every toss-up and bonus from one round PDF.

    pdf_path must sit at raw_root/{level}/{set}/{round}.pdf. If images_dir is given,
    question, answer and whole-question PNGs are written under it. Extract corrections
    (see corrections.yaml) are applied to each question as it is read.
    """
    corrections = corrections or Corrections.empty()
    rel = pdf_path.resolve().relative_to(raw_root.resolve())
    if len(rel.parts) != 3:
        raise ValueError(f"Expected {{level}}/{{set}}/{{round}}.pdf under {raw_root}, got {rel}")
    level, set_name, filename = rel.parts
    round_name = Path(filename).stem

    results: list[RawQuestion] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_i, page in enumerate(pdf.pages):
            lines = group_words_into_lines(pdfplumber.utils.extract_words(normalize_chars(page.chars)))
            render = _PageImage(page, resolution)
            bars = find_fraction_bars(page)
            i = 0
            while i < len(lines):
                part = _is_header(lines[i]["text"])
                if not part:
                    i += 1
                    continue

                entire = _Box(lines[i])
                qbox = _Box(lines[i])
                raw_lines = [lines[i]["text"]]
                i += 1

                found = None
                skipped: list[dict] = []
                for _ in range(3):
                    if i >= len(lines):
                        break
                    found = _match_question_line(lines[i]["text"])
                    if found:
                        break
                    skipped.append(lines[i])
                    i += 1
                if not found:
                    log.debug("%s page %d: no question after %s header", rel, page_i + 1, part)
                    i += 1
                    continue

                num, subj, style, first_text = found
                question_lines = [first_text] if first_text.strip() else []
                # Lines between the header and the "N) SUBJECT" line belong to the question: a superscript
                # or subscript in the first line can push its words above the number. Prose goes back at
                # the start of the text; stray math pieces (exponents, numerators) stay only in the images.
                for line in skipped:
                    qbox.add(line)
                    entire.add(line)
                    raw_lines.append(line["text"])
                lead_style, lead = _split_style(" ".join(line["text"] for line in skipped))
                if _is_prose(lead):
                    style = style or lead_style
                    question_lines = [lead] + question_lines
                qbox.add(lines[i])
                entire.add(lines[i])
                raw_lines.append(lines[i]["text"])
                i += 1

                # Read the body. A line after a choice that isn't a new choice continues that choice.
                # A line reaching into the ANSWER row may be part of the answer (a fraction's numerator set
                # above the word ANSWER), or question math whose text sits lower than it is drawn. Positions
                # can't tell them apart, so such text is kept but marked, and the question image always
                # stops above the ANSWER row.
                answer_top = _next_answer_top(lines, i)
                in_answer_row = False
                row_top = answer_top  # top of everything printed in the ANSWER row
                body: list[tuple[str | None, str]] = []  # (choice letter or None, text)
                while i < len(lines):
                    text = lines[i]["text"]
                    if (_starts_new_question(text) or _is_header(text) or ANSWER_REGEX.match(text)
                            or ROUND_END_REGEX.match(text)):
                        break
                    if _is_footer(text):
                        raw_lines.append(text)
                        i += 1
                        continue
                    if answer_top is not None and lines[i]["y1"] > answer_top + ANSWER_ROW_TOLERANCE:
                        in_answer_row = True
                        row_top = min(row_top, lines[i]["y0"])
                    qbox.add(lines[i])
                    entire.add(lines[i])
                    raw_lines.append(text)
                    c = CHOICE_REGEX.match(text)
                    if c:
                        body.append((c.group(1).upper(), c.group(2) or ""))
                    elif body and body[-1][0]:
                        body[-1] = (body[-1][0], f"{body[-1][1]} {text}")
                    else:
                        body.append((None, text))
                    i += 1

                letters = {letter for letter, _ in body if letter}
                if style:
                    style = style.strip()
                    # A question printing all four choices is multiple choice, whatever its label says.
                    if letters == set("WXYZ"):
                        style = "Multiple Choice"
                else:
                    style = "Multiple Choice" if letters == set("WXYZ") else _guess_style(" ".join(question_lines))
                choices: dict[str, str] | None = None
                if style.lower() == "multiple choice":
                    choices = {letter: text for letter, text in body if letter}
                    question_lines += [text for letter, text in body if not letter]
                else:
                    question_lines += [f"{letter}) {text}" if letter else text for letter, text in body]

                rq = RawQuestion(
                    level=level,
                    set=set_name,
                    round=round_name,
                    pdf=rel.as_posix(),
                    page=page_i + 1,
                    number=int(num),
                    part=part,
                    subject_raw=subj.strip().title() if subj else "",
                    style="Multiple Choice" if style.lower() == "multiple choice" else "Short Answer",
                    question_lines=question_lines,
                    choices=choices,
                    answer_lines=[],
                    raw_pdf_lines=raw_lines,
                    answer_row_overlap=in_answer_row,
                )
                apply_extract_corrections(rq, corrections)

                abox = None
                if i < len(lines) and ANSWER_REGEX.match(lines[i]["text"]):
                    abox = _Box(lines[i])
                    entire.add(lines[i])
                    rq.answer_lines.append(ANSWER_REGEX.sub("", lines[i]["text"]).strip())
                    raw_lines.append(lines[i]["text"])
                    i += 1
                    while i < len(lines):
                        text = lines[i]["text"]
                        if _starts_new_question(text) or _is_header(text) or ROUND_END_REGEX.match(text):
                            break
                        if _is_footer(text):
                            raw_lines.append(text)
                            i += 1
                            continue
                        abox.add(lines[i])
                        entire.add(lines[i])
                        raw_lines.append(text)
                        rq.answer_lines.append(text)
                        i += 1

                # The question part ends above the ANSWER row; a bar in that row belongs to the answer.
                q_end = qbox.y1 if row_top is None else min(qbox.y1, row_top - 0.5)
                if _has_bar(bars, qbox, q_end):
                    rq.stacked_fractions.append("question")
                if abox and _has_bar(bars, abox):
                    rq.stacked_fractions.append("answer")

                if images_dir is not None:
                    base = f"{level}/{set_name}/{round_name}/q{rq.number:02d}-{rq.part}"
                    # The question image stops above the ANSWER row, so it never shows the answer.
                    q_bottom = None
                    if row_top is not None:
                        q_bottom = max(qbox.y0 + 10, min(qbox.y1 + 5, row_top - 0.5))
                    rq.images["question"] = _crop_box(render, qbox.x0, qbox.y0, qbox.x1, qbox.y1, images_dir,
                                                      f"{base}-question.png", resolution, max_y1=q_bottom)
                    if abox:
                        rq.images["answer"] = _crop_box(render, entire.x0, abox.y0, entire.x1, abox.y1,
                                                        images_dir, f"{base}-answer.png", resolution)
                    rq.images["entire"] = _crop(render, entire, images_dir, f"{base}-entire.png", resolution)

                results.append(rq)
    return results


class _PageImage:
    """A page rendered once, at first use, so each crop doesn't render the page again (QB-29)."""

    def __init__(self, page, resolution: int):
        self.page = page
        self.width = page.width
        self.height = page.height
        self._resolution = resolution
        self._image = None

    def crop(self, bbox: tuple[float, float, float, float]):
        if self._image is None:
            self._image = self.page.to_image(resolution=self._resolution).original
        scale = self._resolution / 72
        left, top = self.page.bbox[0], self.page.bbox[1]
        x0, y0, x1, y1 = bbox
        return self._image.crop((round((x0 - left) * scale), round((y0 - top) * scale),
                                 round((x1 - left) * scale), round((y1 - top) * scale)))


def _crop(page: _PageImage, box: _Box, images_dir: Path, rel_name: str, resolution: int) -> str:
    return _crop_box(page, box.x0, box.y0, box.x1, box.y1, images_dir, rel_name, resolution)


def _crop_box(page: _PageImage, x0, y0, x1, y1, images_dir: Path, rel_name: str, resolution: int, margin: float = 5,
              max_y1: float | None = None) -> str:
    out = images_dir / rel_name
    out.parent.mkdir(parents=True, exist_ok=True)
    bottom = min(page.height, y1 + margin)
    if max_y1 is not None:
        bottom = min(bottom, max_y1)
    bbox = (max(0, x0 - margin), max(0, y0 - margin), min(page.width, x1 + margin), bottom)
    # Saved the way pdfplumber saves page images: 256-colour palette PNG, with the resolution recorded.
    image = page.crop(bbox).quantize(256, method=Image.Quantize.FASTOCTREE).convert("P")
    image.save(out, format="PNG", bits=8, dpi=(resolution, resolution))
    return f"images/{rel_name}"
