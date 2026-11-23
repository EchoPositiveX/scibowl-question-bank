"""Parser tests (QB-02). Each runs on a single round without images, so the suite stays fast."""

import json
from pathlib import Path

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb.convert import clean_question_text, split_answer, to_question
from scibowl_qb.extract import extract_round, parse_round_number
from scibowl_qb.parse import main as parse_main
from scibowl_qb.validate import validate_question_set

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-question-set.json"


@pytest.fixture(scope="module")
def set01_round01():
    raw = extract_round(RAW_DIR / "ms/set01/m_round01.pdf", RAW_DIR)
    return {q["id"]: q for q in (to_question(rq) for rq in raw)}


@pytest.fixture(scope="module")
def set13_round01():
    raw = extract_round(RAW_DIR / "ms/set13/2019-NSB-MSR-Round-1A.pdf", RAW_DIR)
    return {q["id"]: q for q in (to_question(rq) for rq in raw)}


def test_round_has_every_tossup_and_bonus(set01_round01):
    assert len(set01_round01) == 50
    for n in range(1, 26):
        assert f"ms-set01-m-round01-q{n:02d}-tossup" in set01_round01
        assert f"ms-set01-m-round01-q{n:02d}-bonus" in set01_round01


def test_round_output_is_valid(set01_round01, set13_round01):
    for questions in (set01_round01, set13_round01):
        data = {"schema_version": 1, "questions": list(questions.values())}
        assert validate_question_set(data) == []


@pytest.mark.parametrize(
    "qid",
    [
        "ms-set01-m-round01-q01-tossup",
        "ms-set01-m-round01-q01-bonus",
        "ms-set01-m-round01-q02-tossup",
        "ms-set13-2019-nsb-msr-round-1a-q01-tossup",
        "ms-set13-2019-nsb-msr-round-1a-q02-tossup",
        "ms-set13-2019-nsb-msr-round-1a-q03-bonus",
    ],
)
def test_matches_hand_checked_sample(qid, set01_round01, set13_round01):
    """Questions the parser already gets right should match the hand-made sample exactly."""
    expected = {q["id"]: q for q in json.loads(SAMPLE.read_text(encoding="utf-8"))["questions"]}[qid]
    got = {**set01_round01, **set13_round01}[qid]
    assert got["question"]["text"] == expected["question"]["text"]
    assert got["answer"]["text"] == expected["answer"]["text"]
    assert got["format"] == expected["format"]
    assert got["category_raw"] == expected["category_raw"]
    assert got["source"]["page"] == expected["source"]["page"]
    assert got["answer"].get("accept", []) == expected["answer"].get("accept", [])
    assert got["answer"].get("do_not_accept", []) == expected["answer"].get("do_not_accept", [])


def test_multiple_choice_is_read(set01_round01):
    q = set01_round01["ms-set01-m-round01-q02-bonus"]
    assert q["format"] == "multiple_choice"
    assert {k: v["text"] for k, v in q["choices"].items()} == {"W": "stationary", "X": "low", "Y": "constant", "Z": "used"}
    assert q["answer"]["choice"] == "W"


def test_style_prefix_is_removed(set13_round01):
    text = set13_round01["ms-set13-2019-nsb-msr-round-1a-q01-tossup"]["question"]["text"]
    assert not text.startswith("–")
    assert "Short Answer" not in text


@pytest.mark.parametrize(
    "lines, expected",
    [
        (["– Short Answer What is the term for", "the point?"], "What is the term for the point?"),
        (["Multiple Choice Which of the following"], "Which of the following"),
        (["What is 2 + 2?"], "What is 2 + 2?"),
    ],
)
def test_clean_question_text(lines, expected):
    assert clean_question_text(lines) == expected


def test_split_answer_accept_and_pronunciation():
    a = split_answer("GEOSTATIONARY (ACCEPT: GEOSYNCHRONOUS EARTH ORBIT; DO NOT\nACCEPT GEOSYNCHRONOUS)", False)
    assert a["text"] == "GEOSTATIONARY"
    assert a["accept"] == ["GEOSYNCHRONOUS EARTH ORBIT"]
    assert a["do_not_accept"] == ["GEOSYNCHRONOUS"]

    b = split_answer("TYCHO BRAHE [TEE-koh BRAH-hay]", False)
    assert b["text"] == "TYCHO BRAHE"
    assert b["pronunciation"] == "TEE-koh BRAH-hay"

    c = split_answer("W) STATIONARY", True)
    assert (c["choice"], c["text"]) == ("W", "STATIONARY")


@pytest.mark.parametrize(
    "name, number",
    [("m_round01", 1), ("Round-10C-MS", 10), ("2019-NSB-MSR-Round-1A", 1), ("14A_MS_Reg_2016", 14),
     ("2020-MS-Rd17", 17), ("2022-MS-3", 3), ("rr5_for_web", 19), ("no_number", None)],
)
def test_round_number(name, number):
    assert parse_round_number(name) == number


def test_cli_one_round(tmp_path, capsys):
    assert parse_main(["--set", "set01", "--round", "m_round01", "--no-images", "--out", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "questions.json").read_text(encoding="utf-8"))
    assert len(data["questions"]) == 50
    assert (tmp_path / "rounds/ms/set01/m_round01.json").exists()
    assert "valid" in capsys.readouterr().out
