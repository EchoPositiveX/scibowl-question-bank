"""Tests for the question format (QB-01): the schema and the extra validation rules."""

import copy
import json
from pathlib import Path

import pytest

from scibowl_qb.validate import expected_id, main, validate_question_set

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-question-set.json"


@pytest.fixture
def sample():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def first(sample, **match):
    return next(q for q in sample["questions"] if all(q.get(k) == v for k, v in match.items()))


def test_sample_file_is_valid(sample):
    assert validate_question_set(sample) == []


def test_cli_reports_ok_and_failure(tmp_path, sample, capsys):
    assert main([str(SAMPLE)]) == 0
    bad = copy.deepcopy(sample)
    bad["schema_version"] = 2
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert main([str(path)]) == 1
    assert "problem" in capsys.readouterr().out


def test_id_is_built_from_source(sample):
    q = first(sample, format="multiple_choice")
    assert expected_id(q) == "ms-set01-m-round01-q02-bonus"


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda q: q.update(part="toss-up"), "is not one of"),
        (lambda q: q.update(category="Earth Science"), "is not one of"),
        (lambda q: q["answer"].update(text=""), "should be non-empty"),
        (lambda q: q.update(extra_field=1), "Additional properties"),
        (lambda q: q["quality"].update(text_status="maybe"), "is not one of"),
    ],
)
def test_schema_rejects_bad_fields(sample, mutate, message):
    mutate(sample["questions"][0])
    problems = validate_question_set(sample)
    assert any(message in p for p in problems), problems


def test_duplicate_ids_are_rejected(sample):
    sample["questions"].append(copy.deepcopy(sample["questions"][0]))
    assert any("duplicate id" in p for p in validate_question_set(sample))


def test_id_must_match_source(sample):
    sample["questions"][0]["number"] = 9
    assert any("does not match its source" in p for p in validate_question_set(sample))


def test_multiple_choice_needs_choices_and_letter(sample):
    q = first(sample, format="multiple_choice")
    del q["answer"]["choice"]
    assert any("no choice letter" in p for p in validate_question_set(sample))
    q["choices"] = None
    assert any("has no choices" in p for p in validate_question_set(sample))


def test_short_answer_cannot_have_choices(sample):
    sa = first(sample, format="short_answer")
    mc = first(sample, format="multiple_choice")
    sa["choices"] = copy.deepcopy(mc["choices"])
    assert any("short answer question has choices" in p for p in validate_question_set(sample))
