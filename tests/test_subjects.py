"""Subject labels and categories (QB-07). Each test reads a single round without images."""

from functools import lru_cache

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb import corrections as corr
from scibowl_qb.convert import category_for, to_question
from scibowl_qb.extract import _match_question_line, extract_round


@lru_cache(maxsize=None)
def _round(pdf_rel: str) -> dict:
    corrections = corr.load()
    raw = extract_round(RAW_DIR / pdf_rel, RAW_DIR, corrections=corrections)
    return {q["id"]: q for q in (corr.apply_question_corrections(to_question(rq), corrections) for rq in raw)}


@pytest.mark.parametrize(
    "line, expected",
    [
        ("3) Math Short Answer What is 2 + 2?", ("3", "Math", "Short Answer", "What is 2 + 2?")),
        ("2) Earth & Space – Short Answer What planet", ("2", "Earth & Space", "Short Answer", "What planet")),
        ("9) LIFE SCIENCE. Multiple Choice Flowering plants", ("9", "LIFE SCIENCE", "Multiple Choice", "Flowering plants")),
        ("12) ENERGYMultiple Choice Researchers are", ("12", "ENERGY", "Multiple Choice", "Researchers are")),
        ("6) EARTH SCIENCE Which of the following is", ("6", "EARTH SCIENCE", None, "Which of the following is")),
        ("18) Math Math Find the product", ("18", "Math", None, "Find the product")),
        ("20) PHYSICAL SCIENCE", ("20", "PHYSICAL SCIENCE", None, "")),
        # No subject printed: the words stay in the question.
        ("16) What is the most common term given to the", ("16", "", None, "What is the most common term given to the")),
    ],
)
def test_match_question_line(line, expected):
    assert _match_question_line(line) == expected


@pytest.mark.parametrize(
    "label, category",
    [
        ("Life Science", "life_science"),
        ("Earth & Space", "earth_and_space"),
        ("Earth And Space Science", "earth_and_space"),
        ("Earth Science", "earth_and_space"),
        ("Mathematics", "math"),
        ("General Science", "general_science"),
        ("Physics", "physics"),
        ("Astrology", None),
        ("", None),
    ],
)
def test_category_for(label, category):
    assert category_for(label) == category


def test_every_question_in_a_round_has_a_category():
    for q in _round("ms/set14/2020-MS-Rd1.pdf").values():
        assert q["category"] is not None, q["id"]


def test_earth_and_space_round():
    # Set 14 prints "Earth & Space – Multiple Choice"; the "&" used to cut the subject short.
    q = _round("ms/set14/2020-MS-Rd1.pdf")["ms-set14-2020-ms-rd1-q15-bonus"]
    assert q["category"] == "earth_and_space"
    assert q["category_raw"] == "Earth & Space"
    assert q["format"] == "multiple_choice"
    assert q["question"]["text"].startswith("Which of the following minerals")


def test_question_start_above_the_number_line():
    # A superscript (10^-4) pushes the first line of the question above "20) PHYSICAL SCIENCE".
    q = _round("ms/set07/MS_Round-3.pdf")["ms-set07-ms-round-3-q20-bonus"]
    assert q["category"] == "physical_science"
    assert q["question"]["text"].startswith("Electromagnetic radiation that has a wavelength of 10-4 meters")


def test_question_text_after_a_glued_subject():
    q = _round("ms/set08/Round-17-A.pdf")["ms-set08-round-17-a-q12-bonus"]
    assert q["category"] == "energy"
    assert q["format"] == "multiple_choice"
    assert q["question"]["text"].startswith("Researchers are beginning to focus on butanol")


def test_wrapped_choice_stays_with_its_choice():
    q = _round("ms/set10/13A_MS_Reg_2016.pdf")["ms-set10-13a-ms-reg-2016-q13-tossup"]
    assert q["choices"]["W"]["text"].endswith("by small angles")
    assert not q["question"]["text"].endswith("angles")


def test_four_printed_choices_make_multiple_choice():
    # Labelled Short Answer in the PDF, but it prints W) to Z) and answers with a letter.
    q = _round("ms/set09/RegionalMS_8A.pdf")["ms-set09-regionalms-8a-q03-tossup"]
    assert q["format"] == "multiple_choice"
    assert q["answer"]["choice"] == "Z"
