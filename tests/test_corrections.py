"""Tests for corrections.yaml (QB-04)."""

import textwrap

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb import corrections as corr
from scibowl_qb.convert import to_question
from scibowl_qb.extract import extract_round
from scibowl_qb.parse import main as parse_main


def write(tmp_path, text):
    path = tmp_path / "corrections.yaml"
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def test_repo_corrections_file_loads():
    c = corr.load()
    assert c.extract
    assert all(e.reason for e in c.extract)


@pytest.mark.parametrize(
    "text, message",
    [
        ("extra: []\n", "unknown top-level keys"),
        ("extract:\n  - match: {set: set01}\n    set: {number: 2}\n", "missing 'reason'"),
        ("extract:\n  - match: {colour: red}\n    set: {number: 2}\n    reason: x\n", "can't match on"),
        ("extract:\n  - match: {set: set01}\n    set: {answer: x}\n    reason: x\n", "can't set"),
        ("questions:\n  - id: a\n    set: {x: 1}\n    reason: r\n  - id: a\n    set: {y: 1}\n    reason: r\n", "more than once"),
    ],
)
def test_bad_files_are_rejected(tmp_path, text, message):
    with pytest.raises(corr.CorrectionsError, match=message):
        corr.load(write(tmp_path, text))


def test_extract_correction_changes_number_and_records_reason():
    pdf = RAW_DIR / "ms/set02/sample_questions_r3.pdf"
    without = {(q.number, q.part) for q in extract_round(pdf, RAW_DIR)}
    assert (46, "bonus") in without and (2, "bonus") not in without

    c = corr.load()
    raw = extract_round(pdf, RAW_DIR, corrections=c)
    fixed = next(q for q in raw if (q.number, q.part) == (2, "bonus"))
    question = to_question(fixed)
    assert "corrected" in question["quality"]["flags"]
    assert any("belongs with toss-up 2" in n for n in question["quality"]["notes"])


def test_question_correction_sets_dotted_paths(tmp_path):
    path = write(tmp_path, """
        questions:
          - id: ms-set01-m-round01-q01-tossup
            set:
              answer.text: NUCLEUS (corrected)
              quality.text_status: verified
            reason: Example fix
    """)
    c = corr.load(path)
    q = to_question(extract_round(RAW_DIR / "ms/set01/m_round01.pdf", RAW_DIR)[0])
    corr.apply_question_corrections(q, c)
    assert q["answer"]["text"] == "NUCLEUS (corrected)"
    assert q["quality"]["text_status"] == "verified"
    assert "corrected" in q["quality"]["flags"]
    assert "Corrected: Example fix" in q["quality"]["notes"]
    assert c.unused_question_corrections() == []


def test_question_correction_cannot_change_id(tmp_path):
    path = write(tmp_path, """
        questions:
          - id: ms-set01-m-round01-q01-tossup
            set: {source.page: 3}
            reason: no
    """)
    q = to_question(extract_round(RAW_DIR / "ms/set01/m_round01.pdf", RAW_DIR)[0])
    with pytest.raises(corr.CorrectionsError, match="extract correction"):
        corr.apply_question_corrections(q, corr.load(path))


def test_parse_fails_on_correction_for_missing_question(tmp_path):
    path = write(tmp_path, """
        questions:
          - id: ms-set01-m-round01-q99-tossup
            set: {answer.text: X}
            reason: typo in the ID
    """)
    args = ["--set", "set01", "--round", "m_round01", "--no-images", "--out", str(tmp_path / "out"), "--corrections", str(path)]
    assert parse_main(args) == 1
