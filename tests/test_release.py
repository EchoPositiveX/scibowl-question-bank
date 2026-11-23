"""Content checks (QB-06), parallel parsing and release files (QB-09). Single rounds only, so it stays fast."""

import copy
import json
import zipfile
from pathlib import Path

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb import corrections as corr
from scibowl_qb.checks import check_question, run_checks
from scibowl_qb.parse import parse_pdfs
from scibowl_qb.release import VERSION, build_manifest, zip_images

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-question-set.json"


@pytest.fixture
def sample():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def _names(q):
    return {name for name, _ in check_question(q)}


def test_sample_has_no_content_problems(sample):
    assert run_checks(sample["questions"]) == []


@pytest.mark.parametrize(
    "change, check",
    [
        (lambda q: q["answer"].update(text="[answer not found by parser]"), "answer_missing"),
        (lambda q: q.update(category=None), "category_missing"),
        (lambda q: q["answer"].update(text="GAMMA Round 3 Page 4"), "footer_text"),
        (lambda q: q["question"].update(text="What is it? ANSWER: GAMMA"), "answer_in_question"),
        (lambda q: q["answer"].update(text="X" * 301), "answer_too_long"),
        (lambda q: q["question"].update(text="Which? W) a X) b Y) c Z) d"), "choices_in_text"),
    ],
)
def test_each_check_fires(sample, change, check):
    q = copy.deepcopy(next(q for q in sample["questions"] if q["format"] == "short_answer"))
    change(q)
    assert check in _names(q)


def test_multiple_choice_checks(sample):
    q = copy.deepcopy(next(q for q in sample["questions"] if q["format"] == "multiple_choice"))
    del q["choices"]["Z"]
    q["choices"]["W"]["text"] = "?"
    assert {"choices_incomplete", "choice_text_missing"} <= _names(q)


def test_flagged_problems_are_not_errors(sample):
    q = copy.deepcopy(sample["questions"][0])
    q["answer"]["text"] = "[answer not found by parser]"
    q["quality"]["flags"] = ["needs_review"]
    (finding,) = run_checks([q])
    assert finding.flagged


def test_parallel_parse_matches_serial(tmp_path):
    pdfs = sorted((RAW_DIR / "ms" / "set16").glob("2022-MS-[12].pdf"))
    c = corr.load()
    serial = parse_pdfs(pdfs, RAW_DIR, tmp_path / "a", images=False, corrections=c)
    parallel = parse_pdfs(pdfs, RAW_DIR, tmp_path / "b", images=False, corrections=c, jobs=2)
    assert [qs for qs in serial.values()] == [qs for qs in parallel.values()]


def test_closing_script_is_not_in_the_last_answer(tmp_path):
    pdf = RAW_DIR / "ms" / "set16" / "2022-MS-1.pdf"
    (questions,) = parse_pdfs([pdf], RAW_DIR, tmp_path, images=False, corrections=corr.load()).values()
    last = next(q for q in questions if q["id"] == "ms-set16-2022-ms-1-q18-bonus")
    assert "Scorekeeper" not in last["answer"]["raw"]
    assert last["answer"]["text"] == "57.5"


@pytest.mark.parametrize("tag, ok", [("v1.0.0", True), ("1.2.3", True), ("v1.0", False), ("latest", False)])
def test_version_format(tag, ok):
    assert bool(VERSION.match(tag)) == ok


def test_manifest_and_zip(tmp_path, sample):
    images = tmp_path / "images" / "ms" / "set01" / "m_round01"
    images.mkdir(parents=True)
    (images / "q01-tossup-question.png").write_bytes(b"png")
    out_zip = tmp_path / "images.zip"
    assert zip_images(tmp_path / "images", out_zip) == 1
    assert zipfile.ZipFile(out_zip).namelist() == ["images/ms/set01/m_round01/q01-tossup-question.png"]

    qfile = tmp_path / "questions.json"
    qfile.write_text(json.dumps(sample), encoding="utf-8")
    m = build_manifest("1.0.0", sample, {"questions.json": qfile, "images.zip": out_zip}, 1)
    assert m["dataset_version"] == "1.0.0"
    assert m["question_count"] == len(sample["questions"])
    assert set(m["files"]) == {"questions.json", "images.zip"}
    assert len(m["files"]["images.zip"]["sha256"]) == 64


def test_preview_page(sample):
    from scibowl_qb.preview import render

    page = render(sample, "Test preview")
    assert page.startswith("<!doctype html>")
    assert "Test preview" in page
    for q in sample["questions"]:
        assert f"id='{q['id']}'" in page
    assert "<script" not in page  # only the inline checkbox handler


def test_count_problems():
    from scibowl_qb.parse import count_problems

    def qs(set_name, n):
        return [{"source": {"level": "ms", "set": set_name}} for _ in range(n)]

    assert count_problems(qs("set16", 324)) == []
    assert count_problems(qs("set04", 847)) == []  # 3 known missing
    assert count_problems(qs("set16", 323)) == ["ms/set16: found 323, expected 324"]
    assert "no expected count" in count_problems(qs("set99", 5))[0]
