"""Extract raw question records from one NSB round PDF.

Ported from the old `nsb` repo's `src/parse_pdf.py` (NSBParser) with the same
line-grouping and regex logic, so results match the old parser. Differences:

- Paths are passed in explicitly instead of being read from the current directory.
- Image cropping is optional (it is the slow part), and images go to a folder you choose.
- The output is a list of `RawQuestion` records; `convert.py` turns them into the
  published question format.

Known problems (page footers in answers, questions split across pages, and so on)
are deliberately left as they were. They have their own roadmap items.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

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
CHOICE_REGEX = re.compile(r"([WXYZ])\)\s+(.*)", re.IGNORECASE)
NEW_QUESTION_REGEX = re.compile(r"\d+\)\s+")

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
    cleaned = re.sub(r"\b(2016|2019|2020|2021)\b", "", round_name.lower())
    match = re.search(r"\d+", cleaned)
    return int(match.group()) if match else None


# Fixes for specific questions whose PDFs are wrong or misleading.
# Each entry: (conditions that must all match, values to set). QB-04 moves these to a file.
OVERRIDES: list[tuple[dict, dict]] = [
    ({"level": "ms", "set": "set02", "round": "sample_questions_r3", "part": "bonus", "number": 46}, {"number": 2}),
    ({"level": "ms", "set": "set02", "round": "sample_questions_r7", "page": 6, "number": 10}, {"number": 12}),
    ({"level": "ms", "set": "set02", "round": "sample_questions_r6", "page": 6, "number": 10}, {"number": 12}),
    ({"level": "ms", "set": "set02", "round": "sample_questions_r8", "page": 6, "number": 10, "part": "bonus"}, {"number": 12}),
    ({"level": "ms", "set": "set02", "round": "sample_questions_r6", "page": 4, "number": 2, "part": "bonus"}, {"number": 8}),
    ({"level": "ms", "set": "set10", "round": "14A_MS_Reg_2016", "page": 8, "number": 16, "part": "tossup",
      "question_lines_start": "– Multiple Choice A discharged capacitor"}, {"part": "bonus"}),
    ({"level": "ms", "set": "set08", "round": "Round-17-A", "page": 9, "number": 18, "part": "tossup",
      "subject_raw": "Math Math"}, {"subject_raw": "Math"}),
]


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

    @property
    def round_number(self) -> int | None:
        return parse_round_number(self.round)

    def _override_value(self, key: str):
        if key == "question_lines_start":
            return "\n".join(self.question_lines)
        return getattr(self, key)

    def apply_overrides(self) -> None:
        for conditions, values in OVERRIDES:
            matched = True
            for key, expected in conditions.items():
                actual = self._override_value(key)
                if key == "question_lines_start":
                    matched = matched and actual.startswith(expected)
                else:
                    matched = matched and actual == expected
            if matched:
                for key, value in values.items():
                    setattr(self, key, value)
                self.overrides_applied.append(f"Override {conditions} -> {values}")
                log.info("Applied override %s -> %s", conditions, values)


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


def _is_header(text: str) -> str | None:
    upper = text.upper()
    if "TOSS-UP" in upper:
        return "tossup"
    if "BONUS" in upper:
        return "bonus"
    return None


def _match_question_line(text: str):
    """Return (number, subject, style, rest) if this line starts a question, else None."""
    m = DEFAULT_QUESTION_REGEX.match(text)
    if m:
        return m.groups()
    m = MISSING_SUBJECT_REGEX.match(text)
    if m:
        num, style, rest = m.groups()
        return num, "", style, rest
    m = SUBJECT_ONLY_REGEX.match(text)
    if m:
        num, subj, rest = m.groups()
        style = "Multiple Choice" if "which of the following" in rest.lower() else "Short Answer"
        return num, subj, style, rest
    return None


def extract_round(pdf_path: Path, raw_root: Path, images_dir: Path | None = None, resolution: int = 300) -> list[RawQuestion]:
    """Extract every toss-up and bonus from one round PDF.

    pdf_path must sit at raw_root/{level}/{set}/{round}.pdf. If images_dir is given,
    question, answer and whole-question PNGs are written under it.
    """
    rel = pdf_path.resolve().relative_to(raw_root.resolve())
    if len(rel.parts) != 3:
        raise ValueError(f"Expected {{level}}/{{set}}/{{round}}.pdf under {raw_root}, got {rel}")
    level, set_name, filename = rel.parts
    round_name = Path(filename).stem

    results: list[RawQuestion] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_i, page in enumerate(pdf.pages):
            lines = group_words_into_lines(page.extract_words())
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
                for _ in range(3):
                    if i >= len(lines):
                        break
                    found = _match_question_line(lines[i]["text"])
                    if found:
                        break
                    i += 1
                if not found:
                    log.debug("%s page %d: no question after %s header", rel, page_i + 1, part)
                    i += 1
                    continue

                num, subj, style, first_text = found
                qbox.add(lines[i])
                entire.add(lines[i])
                raw_lines.append(lines[i]["text"])
                style = style.strip() if style else "Short Answer"
                choices: dict[str, str] | None = {} if style.lower() == "multiple choice" else None
                question_lines = [first_text]
                i += 1

                while i < len(lines):
                    text = lines[i]["text"]
                    if NEW_QUESTION_REGEX.match(text) or _is_header(text) or text.startswith("ANSWER:"):
                        break
                    qbox.add(lines[i])
                    entire.add(lines[i])
                    raw_lines.append(text)
                    c = CHOICE_REGEX.match(text) if choices is not None else None
                    if c:
                        choices[c.group(1).upper()] = c.group(2)
                    else:
                        question_lines.append(text)
                    i += 1

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
                )
                rq.apply_overrides()

                abox = None
                if i < len(lines) and lines[i]["text"].startswith("ANSWER:"):
                    abox = _Box(lines[i])
                    entire.add(lines[i])
                    rq.answer_lines.append(lines[i]["text"][7:].strip())
                    raw_lines.append(lines[i]["text"])
                    i += 1
                    while i < len(lines):
                        text = lines[i]["text"]
                        if NEW_QUESTION_REGEX.match(text) or _is_header(text):
                            break
                        abox.add(lines[i])
                        entire.add(lines[i])
                        raw_lines.append(text)
                        rq.answer_lines.append(text)
                        i += 1

                if images_dir is not None:
                    base = f"{level}/{set_name}/{round_name}/q{rq.number:02d}-{rq.part}"
                    rq.images["question"] = _crop(page, qbox, images_dir, f"{base}-question.png", resolution)
                    if abox:
                        rq.images["answer"] = _crop_box(page, entire.x0, abox.y0, entire.x1, abox.y1,
                                                        images_dir, f"{base}-answer.png", resolution)
                    rq.images["entire"] = _crop(page, entire, images_dir, f"{base}-entire.png", resolution)

                results.append(rq)
    return results


def _crop(page, box: _Box, images_dir: Path, rel_name: str, resolution: int) -> str:
    return _crop_box(page, box.x0, box.y0, box.x1, box.y1, images_dir, rel_name, resolution)


def _crop_box(page, x0, y0, x1, y1, images_dir: Path, rel_name: str, resolution: int, margin: float = 5) -> str:
    out = images_dir / rel_name
    out.parent.mkdir(parents=True, exist_ok=True)
    bbox = (max(0, x0 - margin), max(0, y0 - margin), min(page.width, x1 + margin), min(page.height, y1 + margin))
    page.crop(bbox).to_image(resolution=resolution).save(out, format="PNG")
    return f"images/{rel_name}"
