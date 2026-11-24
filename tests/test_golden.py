"""Golden tests (QB-05): about 50 questions across all middle school sets, hand-checked against
the printed images, compared field by field with what the parser produces.

Each test parses only its own round (without images), so `pytest -k set06` runs just that set.
Entries with `known_issue` describe a parser bug that is still open; they are expected to fail,
and `strict` makes the test fail once the bug is fixed, as a reminder to remove the note.
"""

from functools import cache
from pathlib import Path

import pytest
import yaml

from scibowl_qb import RAW_DIR
from scibowl_qb import corrections as corr
from scibowl_qb import transcriptions as tr
from scibowl_qb.convert import to_question
from scibowl_qb.extract import extract_round
from scibowl_qb.validate import slugify

GOLDEN = yaml.safe_load((Path(__file__).parent / "golden" / "questions.yaml").read_text(encoding="utf-8"))["questions"]


@cache
def _corrections():
    return corr.load(corr.DEFAULT_PATH)


@cache
def _transcriptions():
    return tr.load()


@cache
def parsed_round(pdf: str) -> dict[str, dict]:
    raw = extract_round(RAW_DIR / pdf, RAW_DIR, corrections=_corrections())
    questions = (tr.apply(corr.apply_question_corrections(to_question(rq), _corrections()), _transcriptions()) for rq in raw)
    return {q["id"]: q for q in questions}


def _pdf_for(qid: str) -> str:
    """The golden file names questions by ID; find the round PDF from the ID's level, set and round slug."""
    level, set_name, rest = qid.split("-", 2)
    round_slug = rest.rsplit("-q", 1)[0]
    matches = [p for p in (RAW_DIR / level / set_name).glob("*.pdf") if slugify(p.stem) == round_slug]
    assert len(matches) == 1, f"{qid}: expected one PDF for round {round_slug!r}, found {matches}"
    return matches[0].relative_to(RAW_DIR).as_posix()


def actual_fields(q: dict) -> dict:
    a = q["answer"]
    fields = {"category": q["category"], "format": q["format"], "question": q["question"]["text"], "answer.text": a["text"]}
    if q["choices"]:
        fields.update({f"choices.{k}": v["text"] for k, v in q["choices"].items()})
    if a.get("choice"):
        fields["answer.choice"] = a["choice"]
    for key in ("accept", "do_not_accept"):
        if a.get(key):
            fields[f"answer.{key}"] = a[key]
    return fields


def expected_fields(g: dict) -> dict:
    fields = {"category": g["category"], "format": g["format"], "question": g["question"], "answer.text": g["answer"]["text"]}
    fields.update({f"choices.{k}": v for k, v in (g.get("choices") or {}).items()})
    for key in ("choice", "accept", "do_not_accept"):
        if key in g["answer"]:
            fields[f"answer.{key}"] = g["answer"][key]
    return fields


def _param(g: dict):
    marks = [pytest.mark.xfail(reason=g["known_issue"], strict=True)] if g.get("known_issue") else []
    return pytest.param(g, id=g["id"], marks=marks)


def test_golden_file_is_well_formed():
    ids = [g["id"] for g in GOLDEN]
    assert len(ids) == len(set(ids)), "an ID is listed twice"
    assert len(ids) >= 50
    assert len({i.split("-")[1] for i in ids}) == 16, "every middle school set should have golden questions"
    for g in GOLDEN:
        assert (g["format"] == "multiple_choice") == ("choices" in g) == ("choice" in g["answer"]), g["id"]


@pytest.mark.parametrize("golden", [_param(g) for g in GOLDEN])
def test_golden_question(golden):
    questions = parsed_round(_pdf_for(golden["id"]))
    assert golden["id"] in questions, f"{golden['id']} was not found in its round"
    assert actual_fields(questions[golden["id"]]) == expected_fields(golden)
