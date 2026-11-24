"""Turn extracted RawQuestion records into the published question format (schema v1).

This step only reshapes data and does light, safe cleanup:
- joins the PDF's line breaks into normal text,
- removes the "– Short Answer" / "– Multiple Choice" prefix some sets print,
- splits ACCEPT / DO NOT ACCEPT notes and [pronunciation] hints out of answers,
  and splits an ACCEPT that lists several answers (see `split_alternatives`),
- drops a printed "(Solution: ...)" working from the answer (it stays in answer.raw),
- removes a stray space before a final question mark,
- reads the letter of a multiple choice answer,
- drops separator lines (~~~~) printed between questions,
- maps the printed subject label to one of the official categories.

Bigger fixes (page footers, subject names, layout failures) have their own roadmap items,
so anything doubtful is left as is and marked in `quality`.
"""

from __future__ import annotations

import re

from .extract import RawQuestion
from .validate import SCHEMA_VERSION, slugify

STYLE_PREFIX = re.compile(r"^\s*[–—-]?\s*(short answer|multiple choice)\s*:?\s*", re.IGNORECASE)
MC_ANSWER = re.compile(r"^\s*([WXYZ])\)\s*(.*)$", re.IGNORECASE | re.DOTALL)
PRONUNCIATION = re.compile(r"\[([^\]]+)\]")
ACCEPT_NOTE = re.compile(r"\(([^()]*\bACCEPT\b[^()]*)\)", re.IGNORECASE)
MISSING_ANSWER = "[answer not found by parser]"
SEPARATOR_LINE = re.compile(r"^\s*[~_=*-]{5,}\s*$")
SOLUTION_NOTE = re.compile(r"\s*\(\s*Solution\s*:.*$", re.DOTALL)
SPACE_BEFORE_FINAL_QMARK = re.compile(r"(?<=[\w)\]”’°%])\s+\?$")
LOWER_OR = re.compile(r"\s+or\s+")
NUMBER = re.compile(r"^([–—−-])?\s*(?:(\d+)\s+)?(\d+(?:\.\d+)?)(?:\s*/\s*(\d+))?$")

# Printed subject label (lower case, "&" written as "and") -> category.
CATEGORIES = {
    "life science": "life_science",
    "physical science": "physical_science",
    "earth and space": "earth_and_space",
    "earth and space science": "earth_and_space",
    "earth science": "earth_and_space",
    "energy": "energy",
    "math": "math",
    "mathematics": "math",
    "general science": "general_science",
    # High school labels, found in a few rounds.
    "biology": "biology",
    "chemistry": "chemistry",
    "physics": "physics",
}


def category_for(label: str) -> str | None:
    """Official category for a printed subject label, or None if the label isn't known."""
    key = re.sub(r"\s+", " ", label.replace("&", " and ")).strip().lower()
    return CATEGORIES.get(key)


def join_lines(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(line.strip() for line in lines)).strip()


def clean_question_text(lines: list[str]) -> str:
    text = STYLE_PREFIX.sub("", join_lines(lines), count=1).strip()
    return SPACE_BEFORE_FINAL_QMARK.sub("?", text)


def _number(text: str) -> float | None:
    """Value of a plain number, decimal, fraction or mixed number ("6 18/25"), else None."""
    m = NUMBER.match(text.strip())
    if not m or (m.group(2) and not m.group(4)):
        return None
    sign, whole, num, den = m.groups()
    value = float(num) / float(den) if den else float(num)
    if den and float(den) == 0:
        return None
    value += float(whole or 0)
    return -value if sign else value


def split_alternatives(text: str) -> list[str]:
    """Split one printed ACCEPT / DO NOT ACCEPT entry that lists several answers.

    Only two patterns are split, because a comma or an upper case OR is often part of the
    answer itself ("1, 2, AND 4", "Y OR ORDINATE AXIS"):
    - a lower case "or" between upper case answers ("D-GLUCOSE or DEXTROSE"), unless the
      entry also has a comma, a lower case "for", or starts with a sign ("+ or -");
    - commas between numbers that are all the same value written differently ("6 18/25, 6.72").
    """
    parts = [p.strip() for p in LOWER_OR.split(text)]
    if (len(parts) > 1 and all(parts) and "," not in text and " for " not in text
            and parts[0].upper() not in {"+", "-", "–", "PLUS", "MINUS", "NEGATIVE", "POSITIVE"}):
        return parts
    parts = [p.strip() for p in text.split(",")]
    values = [_number(p) for p in parts]
    if (len(parts) > 1 and None not in values and len(set(parts)) == len(parts)
            and max(values) - min(values) < 1e-9):
        return parts
    return [text]


def split_answer(raw: str, is_mc: bool) -> dict:
    """Split a printed answer into main text, choice letter, accept lists and pronunciation."""
    answer: dict = {"raw": raw}
    text = re.sub(r"\s+", " ", raw).strip()

    if is_mc:
        m = MC_ANSWER.match(text)
        if m:
            answer["choice"] = m.group(1).upper()
            text = m.group(2).strip()

    accept: list[str] = []
    do_not_accept: list[str] = []
    for note in ACCEPT_NOTE.findall(text):
        for clause in re.split(r";", note):
            clause = clause.strip()
            dna = re.match(r"^DO NOT ACCEPT\s*:?\s*(.+)$", clause, re.IGNORECASE)
            acc = re.match(r"^ACCEPT\s*:?\s*(.+)$", clause, re.IGNORECASE)
            if dna:
                do_not_accept.extend(split_alternatives(dna.group(1).strip()))
            elif acc:
                accept.extend(split_alternatives(acc.group(1).strip()))
    text = ACCEPT_NOTE.sub("", text)
    text = SOLUTION_NOTE.sub("", text)

    pron = PRONUNCIATION.findall(text)
    text = PRONUNCIATION.sub("", text)

    text = re.sub(r"\s+", " ", text).strip()
    answer["text"] = text
    if accept:
        answer["accept"] = accept
    if do_not_accept:
        answer["do_not_accept"] = do_not_accept
    if pron:
        answer["pronunciation"] = "; ".join(p.strip() for p in pron)
    return answer


def to_question(rq: RawQuestion) -> dict:
    is_mc = rq.style == "Multiple Choice"
    flags: list[str] = []
    notes: list[str] = list(rq.overrides_applied)
    if rq.overrides_applied:
        flags.append("corrected")

    category = category_for(rq.subject_raw)
    if category is None:
        notes.append(f"Unknown subject label: {rq.subject_raw!r}" if rq.subject_raw else "No subject label found")
        flags.append("needs_review")

    if rq.answer_row_overlap:
        # Never show this text before the answer is revealed: it may contain part of the answer.
        notes.append("Some question text sits in the ANSWER row and may be part of the answer; see the question image")
        flags.append("needs_review")

    question_text = clean_question_text(rq.question_lines)
    if not question_text:
        question_text = "[question text not found by parser]"
        flags.append("needs_review")

    choices = None
    if is_mc:
        if rq.choices and set(rq.choices) == {"W", "X", "Y", "Z"}:
            choices = {k: {"text": v.strip() or "?", "latex": None} for k, v in sorted(rq.choices.items())}
            blank = [k for k, v in sorted(rq.choices.items()) if not v.strip()]
            if blank:
                notes.append(f"Choice text missing for {', '.join(blank)} (probably a formula; see the question image)")
                flags.append("needs_review")
        else:
            # Missing choices: record what we have in the notes and treat as short answer for now.
            found = ", ".join(sorted(rq.choices or {})) or "none"
            notes.append(f"Multiple choice but choices found were: {found}")
            flags.append("needs_review")
            is_mc = False

    answer_lines = [line for line in rq.answer_lines if not SEPARATOR_LINE.match(line)]
    raw_answer = "\n".join(answer_lines).strip()
    if raw_answer:
        answer = split_answer(raw_answer, is_mc)
        if not answer["text"]:
            answer["text"] = raw_answer
    else:
        answer = {"text": MISSING_ANSWER, "raw": ""}
        flags.append("needs_review")
        if rq.answer_lines:
            notes.append("The ANSWER line has no text (the answer is probably a formula or picture; see the answer image)")
        else:
            notes.append("No ANSWER line found")
    if is_mc and "choice" not in answer:
        notes.append("Could not read the answer's choice letter")
        flags.append("needs_review")
        is_mc = False
        choices = None
    answer["latex"] = None

    has_images = bool(rq.images.get("question"))
    status = "auto"
    if "needs_review" in flags and has_images:
        status = "images_only"

    return {
        "id": f"{rq.level}-{rq.set}-{slugify(rq.round)}-q{rq.number:02d}-{rq.part}",
        "source": {
            "level": rq.level,
            "set": rq.set,
            "round": rq.round,
            "round_number": rq.round_number,
            "pdf": rq.pdf,
            "page": rq.page,
        },
        "number": rq.number,
        "part": rq.part,
        "category": category,
        "category_raw": rq.subject_raw,
        "format": "multiple_choice" if is_mc else "short_answer",
        "question": {"text": question_text, "latex": None},
        "choices": choices,
        "answer": answer,
        "images": dict(rq.images),
        "tags": {"disciplines": [], "topics": [], "source": None, "reviewed": False},
        "quality": {"text_status": status, "flags": sorted(set(flags)), "notes": notes},
    }


def to_question_set(questions: list[dict], generator: str, generated_at: str | None = None) -> dict:
    data = {"schema_version": SCHEMA_VERSION, "generator": generator, "questions": questions}
    if generated_at:
        data["generated_at"] = generated_at
    return data
