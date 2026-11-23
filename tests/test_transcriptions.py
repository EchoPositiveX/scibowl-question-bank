"""Tests for transcribed text and LaTeX (QB-10)."""

import copy
import json
import textwrap

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb import transcriptions as tr
from scibowl_qb.convert import to_question
from scibowl_qb.extract import extract_round
from scibowl_qb.validate import validate_question_set

ENTRY = """\
questions:
  - id: ms-set01-m-round03-q07-bonus
    question: {text: "Change the decimal 0.88 to a fraction in lowest terms:", latex: "Change the decimal 0.88 to a fraction in lowest terms:"}
    answer: {text: "22/25", latex: "$\\\\frac{22}{25}$"}
    reviewed: %s
"""


def write(tmp_path, text, name="set01.yaml"):
    folder = tmp_path / "ms"
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(textwrap.dedent(text), encoding="utf-8")
    return tmp_path


_PARSED = {}


def parsed(qid="ms-set01-m-round03-q07-bonus"):
    if not _PARSED:
        _PARSED.update({q["id"]: q for q in (to_question(rq) for rq in extract_round(RAW_DIR / "ms/set01/m_round03.pdf", RAW_DIR))})
    return copy.deepcopy(_PARSED[qid])


def test_repo_transcriptions_load_and_are_well_formed():
    loaded = tr.load()
    assert len([t for t in loaded.values() if t.id.startswith("ms-set01-")]) == 28


def test_unreviewed_transcription_keeps_images(tmp_path):
    status_before = parsed()["quality"]["text_status"]
    q = tr.apply(parsed(), tr.load(write(tmp_path, ENTRY % "false")))
    assert q["question"]["text"] == "Change the decimal 0.88 to a fraction in lowest terms:"
    assert q["answer"]["text"] == "22/25"
    assert q["answer"]["latex"] == "$\\frac{22}{25}$"
    assert q["quality"]["text_status"] == status_before  # images_only whenever the round has images
    assert {"needs_review", "has_math"} <= set(q["quality"]["flags"])


def test_reviewed_transcription_is_verified(tmp_path):
    q = tr.apply(parsed(), tr.load(write(tmp_path, ENTRY % "true")))
    assert q["quality"]["text_status"] == "verified"
    assert "needs_review" not in q["quality"]["flags"]
    assert any("checked against it" in n for n in q["quality"]["notes"])


def test_transcribed_question_is_valid(tmp_path):
    q = tr.apply(parsed(), tr.load(write(tmp_path, ENTRY % "true")))
    problems = validate_question_set({"schema_version": 1, "generator": "test", "generated_at": "2026-11-23T00:00:00Z", "questions": [q]})
    assert not [p for p in problems if "image" not in p], problems


def test_other_questions_are_untouched(tmp_path):
    q = parsed("ms-set01-m-round03-q01-tossup")
    before = json.dumps(q, sort_keys=True)
    tr.apply(q, tr.load(write(tmp_path, ENTRY % "false")))
    assert json.dumps(q, sort_keys=True) == before


@pytest.mark.parametrize(
    "text, message",
    [
        ("extra: 1\n", "unknown top-level keys"),
        ("questions:\n  - id: x\n    question: {text: a, latex: a}\n    answer: {text: b, latex: b}\n", "'reviewed'"),
        ("questions:\n  - id: x\n    question: {text: a, latex: '$x'}\n    answer: {text: b, latex: b}\n    reviewed: false\n", "unmatched \\$"),
        ("questions:\n  - id: x\n    question: {text: a}\n    answer: {text: b, latex: b}\n    reviewed: false\n", "'latex'"),
        ("questions:\n  - id: x\n    question: {text: a, latex: a}\n    answer: {text: b, latex: b}\n    choices: {W: {text: a, latex: a}}\n    reviewed: false\n", "W, X, Y and Z"),
    ],
)
def test_bad_files_are_rejected(tmp_path, text, message):
    with pytest.raises(tr.TranscriptionError, match=message):
        tr.load(write(tmp_path, text))


def test_same_question_in_two_files_is_rejected(tmp_path):
    folder = write(tmp_path, ENTRY % "false")
    write(folder, ENTRY % "true", name="again.yaml")
    with pytest.raises(tr.TranscriptionError, match="transcribed in both"):
        tr.load(folder)


def test_choices_must_match_the_format(tmp_path):
    entry = ENTRY % "false"
    entry = entry.replace("    reviewed:", "    choices: {W: {text: a, latex: a}, X: {text: b, latex: b}, Y: {text: c, latex: c}, Z: {text: d, latex: d}}\n    reviewed:")
    with pytest.raises(tr.TranscriptionError, match="choices"):
        tr.apply(parsed(), tr.load(write(tmp_path, entry)))
