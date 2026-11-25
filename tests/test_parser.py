"""Parser tests (QB-02). Each runs on a single round without images, so the suite stays fast."""

import json
from pathlib import Path

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb.convert import clean_question_text, split_alternatives, split_answer, to_question
from scibowl_qb.extract import extract_round, normalize_chars, parse_round_number
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


def test_fraction_bar_is_flagged(set01_round01):
    """1 over 3 comes apart in the PDF text ("convert rd to a decimal: 3"), so the question shows its image."""
    q = set01_round01["ms-set01-m-round01-q14-bonus"]
    assert "needs_review" in q["quality"]["flags"]
    assert "Fraction or root bar in the question; the text may be wrong, see the image" in q["quality"]["notes"]
    # A question with no fraction stays as it was.
    assert "needs_review" not in set01_round01["ms-set01-m-round01-q02-bonus"]["quality"]["flags"]


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
        (["What is the distance between (2, 5) and (6, 8) ?"], "What is the distance between (2, 5) and (6, 8)?"),
        (["Water boils at 100°C ?"], "Water boils at 100°C?"),
        (["Which value is missing: 3, ? , 7"], "Which value is missing: 3, ? , 7"),
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


def test_split_answer_drops_solution_note():
    a = split_answer("6 (Solution: input distance/output distance: 24/4 = 6)", False)
    assert a["text"] == "6"
    assert "Solution" in a["raw"]
    assert split_answer("WHETHER A SOLUTION IS ACIDIC OR BASIC", False)["text"] == "WHETHER A SOLUTION IS ACIDIC OR BASIC"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("D-GLUCOSE or DEXTROSE", ["D-GLUCOSE", "DEXTROSE"]),
        ("ER or RER or ROUGH ER", ["ER", "RER", "ROUGH ER"]),
        ("6 18/25, 6.72", ["6 18/25", "6.72"]),
        ("1/2, 0.5, 50/100", ["1/2", "0.5", "50/100"]),
        # Left alone: a comma or upper case OR is usually part of the answer.
        ("1, 2, 3, AND 4 OR ALL", ["1, 2, 3, AND 4 OR ALL"]),
        ("WHERE THE LINE CROSSES THE Y OR ORDINATE AXIS", ["WHERE THE LINE CROSSES THE Y OR ORDINATE AXIS"]),
        ("TESLA, GEORGE WESTINGHOUSE, or WESTINGHOUSE", ["TESLA, GEORGE WESTINGHOUSE, or WESTINGHOUSE"]),
        ("MEDIUM or BETWEEN for MIDDLE", ["MEDIUM or BETWEEN for MIDDLE"]),
        ("+ or - 1", ["+ or - 1"]),
        ("NEGATIVE or MINUS 90", ["NEGATIVE or MINUS 90"]),
        ("60, 60, 60", ["60, 60, 60"]),
        ("2, 4, 1, 3", ["2, 4, 1, 3"]),
        ("418,000", ["418,000"]),
    ],
)
def test_split_alternatives(text, expected):
    assert split_alternatives(text) == expected


def _char(text, x0, top, size, bottom=None):
    return {"text": text, "x0": x0, "x1": x0 + size * 0.6, "top": top, "doctop": top,
            "bottom": bottom if bottom is not None else top + size, "size": size}


def test_normalize_chars_subscripts_and_degree_sign():
    # "NH3" with a lowered, smaller 3, and "100oC" with a raised, smaller o.
    nh3 = [_char("N", 10, 100, 12), _char("H", 17.2, 100, 12), _char("3", 24.4, 104.3, 8, bottom=112.3)]
    out = normalize_chars(nh3)
    assert {c["top"] for c in out} == {100}
    assert nh3[2]["top"] == 104.3, "the input is not changed"

    deg = [_char("1", 10, 100, 12), _char("0", 17.2, 100, 12), _char("0", 24.4, 100, 12),
           _char("o", 31.6, 99, 8, bottom=105), _char("C", 36.4, 100, 12)]
    assert "".join(c["text"] for c in normalize_chars(deg)) == "100°C"

    # A small letter that is not raised, or not after a digit, is left alone.
    plain = [_char("x", 10, 100, 12), _char("o", 17.2, 99, 8, bottom=105)]
    assert "".join(c["text"] for c in normalize_chars(plain)) == "xo"


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


# Questions the PDFs print with a slip in the label: "17 LIFE SCIENCE" with no ")", and "TOSS- UP" with a space.
# Each used to be dropped, leaving its tossup or bonus without a partner.
@pytest.mark.parametrize("pdf, qid, starts", [
    ("ms/set02/sample_questions_r6.pdf", "ms-set02-sample-questions-r6-q04-bonus", "Assuming a year in a dog"),
    ("ms/set04/Round6.pdf", "ms-set04-round6-q17-bonus", "There are two main kinds of vaccines"),
    ("ms/set04/Round8.pdf", "ms-set04-round8-q03-tossup", "In order to figure out what is in a sealed box"),
    ("ms/set04/Round15.pdf", "ms-set04-round15-q04-tossup", "Which of the following natural resources"),
])
def test_question_with_a_misprinted_label_is_read(pdf, qid, starts):
    from scibowl_qb import corrections as corr
    questions = {q["id"]: q for q in (to_question(rq) for rq in
                 extract_round(RAW_DIR / pdf, RAW_DIR, corrections=corr.load()))}
    assert questions[qid]["question"]["text"].startswith(starts)
    for q in questions.values():
        assert "TOSS" not in q["answer"]["text"].upper(), q["id"]
