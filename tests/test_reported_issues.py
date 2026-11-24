"""Regression tests for reported question problems (QB-21).

Every fixed issue adds a case to REPORTED: the issue number, the question ID,
and the values that should now be right. See docs/fixing-questions.md.
"""

from functools import lru_cache

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb import corrections as corr
from scibowl_qb.convert import to_question
from scibowl_qb.extract import extract_round

# (issue number, question id, {dotted.path: expected value})
REPORTED: list[tuple[int, str, dict]] = [
    # Example:
    # (12, "ms-set13-2019-nsb-msr-round-1a-q03-tossup", {"answer.text": "25", "quality.text_status": "verified"}),
]


@lru_cache(maxsize=None)
def _round(pdf_rel: str) -> dict:
    corrections = corr.load()
    raw = extract_round(RAW_DIR / pdf_rel, RAW_DIR, corrections=corrections)
    questions = [corr.apply_question_corrections(to_question(rq), corrections) for rq in raw]
    return {q["id"]: q for q in questions}


def _find(question_id: str) -> dict:
    for pdf in sorted(RAW_DIR.glob("*/*/*.pdf")):
        level, set_name = pdf.parent.parent.name, pdf.parent.name
        if question_id.startswith(f"{level}-{set_name}-"):
            questions = _round(pdf.relative_to(RAW_DIR).as_posix())
            if question_id in questions:
                return questions[question_id]
    raise AssertionError(f"{question_id} not found")


def _get(question: dict, dotted: str):
    value = question
    for key in dotted.split("."):
        value = value[key]
    return value


@pytest.mark.parametrize("issue, question_id, expected", REPORTED, ids=[f"issue-{r[0]}" for r in REPORTED])
def test_reported_issue_stays_fixed(issue, question_id, expected):
    question = _find(question_id)
    for path, value in expected.items():
        assert _get(question, path) == value, f"issue #{issue}: {path}"


def test_answer_key_error_found_in_review_stays_fixed():
    """Set 13 RR2 toss-up 13 prints Y) x^6; x^8 x^4 / x^2 is x^10 (choice X). Found in QB-36 review."""
    question = _find("ms-set13-rr2-for-web-q13-tossup")
    assert question["answer"]["choice"] == "X"
    assert question["answer"]["text"] == "x^10"
    assert "corrected" in question["quality"]["flags"]


def test_otec_choices_missing_from_pdf_stay_filled_in():
    """Set 04 Round 4 toss-up 21 prints blank images for X, Y and the answer's first digit (QB-37)."""
    question = _find("ms-set04-round4-q21-tossup")
    assert question["choices"]["X"]["text"] == "10"
    assert question["choices"]["Y"]["text"] == "20"
    assert question["answer"]["choice"] == "Y"
    assert question["answer"]["text"] == "20"
    assert question["quality"]["text_status"] == "verified"
    assert "needs_review" not in question["quality"]["flags"]
