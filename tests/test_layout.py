"""Layout fixes (QB-08). Each test reads a single round without images."""

from functools import lru_cache

from scibowl_qb import RAW_DIR
from scibowl_qb import corrections as corr
from scibowl_qb.convert import to_question
from scibowl_qb.extract import ANSWER_REGEX, _is_footer, _starts_new_question, extract_round


@lru_cache(maxsize=None)
def _round(pdf_rel: str) -> dict:
    corrections = corr.load()
    raw = extract_round(RAW_DIR / pdf_rel, RAW_DIR, corrections=corrections)
    return {q["id"]: q for q in (corr.apply_question_corrections(to_question(rq), corrections) for rq in raw)}


def test_numbered_statements_do_not_end_the_question():
    q = _round("ms/set01/m_round07.pdf")["ms-set01-m-round07-q13-tossup"]
    assert q["question"]["text"].endswith("3) a scalene triangle has 2 sides of equal length")
    assert q["answer"]["text"] == "1 AND 2"
    assert "needs_review" not in q["quality"]["flags"]


def test_starts_new_question():
    assert _starts_new_question("13) MATH Short Answer Name all of the following")
    assert _starts_new_question("2) Earth & Space – Short Answer What planet")
    assert not _starts_new_question("1) a square is a regular polygon")
    assert not _starts_new_question("2) an equilateral triangle is equiangular")


def test_answer_spellings():
    for line in ["ANSWER: X", "ANSWER : X", "Answer: X) 2", "ANSWER W) SOLAR"]:
        assert ANSWER_REGEX.match(line), line
    for line in ["ANSWERS are", "Answer the following"]:
        assert not ANSWER_REGEX.match(line), line


def test_answer_with_space_before_colon():
    q = _round("ms/set02/sample_questions_r10.pdf")["ms-set02-sample-questions-r10-q03-tossup"]
    assert q["answer"]["choice"] == "Z"


def test_answer_without_colon():
    q = _round("ms/set08/Round-13-A.pdf")["ms-set08-round-13-a-q14-tossup"]
    assert q["answer"]["choice"] == "W"
    assert q["answer"]["text"].startswith("SOLAR CONSTANT")


def test_footers():
    for line in ["Round 14 Page 9", "Middle School Round 9 Page 8", "11 Middle School Regional NSB® PAGE 3",
                 "Middle School - Round 6A", "******************", "~~~~~~~~~~"]:
        assert _is_footer(line), line
    assert not _is_footer("finished at the bottom of page 255. How many pages did she read?")


def test_footer_not_in_answer():
    q = _round("ms/set04/Round1.pdf")["ms-set04-round1-q02-bonus"]
    assert q["answer"]["text"] == "LAWS OF THERMODYNAMICS"
    q = _round("ms/set14/2020-MS-Rd1.pdf")["ms-set14-2020-ms-rd1-q01-bonus"]
    assert q["answer"]["text"] == "DESERT"


def test_blank_choice_is_kept_and_flagged():
    q = _round("ms/set04/Round4.pdf")["ms-set04-round4-q21-tossup"]
    assert q["format"] == "multiple_choice"
    assert set(q["choices"]) == {"W", "X", "Y", "Z"}
    assert q["answer"]["choice"] == "Y"
    assert "needs_review" in q["quality"]["flags"]
