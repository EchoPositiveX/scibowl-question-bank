"""Content checks across all questions (QB-06).

The schema says what a question looks like; these checks say whether its content
is plausible. The rule is: every problem found here must either be fixed or be
flagged `needs_review` (so the website falls back to images). An unflagged
problem is an error and blocks a release.

Usage:
    python -m scibowl_qb.checks output/questions.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .convert import MISSING_ANSWER

FOOTER_TEXT = re.compile(r"\b(round\s*\d+[a-z]?\s*[-–~,]?\s*page\s*\d+|page\s*\d+\s*$)", re.IGNORECASE)
ANSWER_IN_QUESTION = re.compile(r"\bANSWER\s*:")
PLACEHOLDER = re.compile(r"^\[.*not found by parser\]$")
CHOICES_IN_TEXT = re.compile(r"\bW\)\s.*\bX\)\s.*\bY\)\s.*\bZ\)", re.DOTALL)
LONG_ANSWER = 300  # characters; longer answers usually swallowed the next question


@dataclass
class Finding:
    id: str
    check: str
    detail: str
    flagged: bool  # True if the question is already marked needs_review

    def __str__(self) -> str:
        return f"{self.id}: {self.check}: {self.detail}"


def check_question(q: dict) -> list[tuple[str, str]]:
    """Return (check name, detail) for each content problem in one question."""
    problems = []
    qtext = q["question"]["text"]
    answer = q["answer"]["text"]

    if PLACEHOLDER.match(qtext) or not qtext.strip():
        problems.append(("question_missing", "no question text"))
    if answer == MISSING_ANSWER or not answer.strip():
        problems.append(("answer_missing", "no answer text"))
    if q["category"] is None:
        problems.append(("category_missing", f"unknown subject label {q['category_raw']!r}"))
    if q["format"] == "multiple_choice":
        choices = q["choices"] or {}
        if set(choices) != {"W", "X", "Y", "Z"}:
            problems.append(("choices_incomplete", f"choices {sorted(choices)}"))
        blank = [k for k, v in sorted(choices.items()) if v["text"] in ("", "?")]
        if blank:
            problems.append(("choice_text_missing", f"blank choices {blank}"))
        if q["answer"].get("choice") not in choices:
            problems.append(("answer_choice_invalid", f"answer letter {q['answer'].get('choice')!r}"))
    for field, text in (("question", qtext), ("answer", answer)):
        m = FOOTER_TEXT.search(text)
        if m:
            problems.append(("footer_text", f"{field} contains {m.group(0)!r}"))
    if q["format"] == "short_answer" and CHOICES_IN_TEXT.search(qtext):
        problems.append(("choices_in_text", "short answer question prints W) to Z) choices"))
    if len(answer) > LONG_ANSWER:
        problems.append(("answer_too_long", f"{len(answer)} characters"))
    if ANSWER_IN_QUESTION.search(qtext):
        problems.append(("answer_in_question", "question text contains 'ANSWER:'"))
    return problems


def run_checks(questions: list[dict]) -> list[Finding]:
    findings = []
    for q in questions:
        flagged = "needs_review" in q["quality"]["flags"]
        for check, detail in check_question(q):
            findings.append(Finding(q["id"], check, detail, flagged))
    return findings


def report(findings: list[Finding]) -> str:
    errors = [f for f in findings if not f.flagged]
    known = Counter(f.check for f in findings if f.flagged)
    lines = [f"Known problems on questions flagged needs_review: {sum(known.values())}"]
    lines += [f"  {name}: {n}" for name, n in sorted(known.items())]
    lines.append(f"Unflagged problems (errors): {len(errors)}")
    lines += [f"  - {f}" for f in errors[:50]]
    if len(errors) > 50:
        lines.append(f"  ... and {len(errors) - 50} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__)
        return 2
    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    findings = run_checks(data["questions"])
    print(report(findings))
    return 1 if any(not f.flagged for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
