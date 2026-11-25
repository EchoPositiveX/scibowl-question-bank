"""Tests for topic tags (QB-11, QB-12)."""

import shutil
import textwrap

import pytest

from scibowl_qb import RAW_DIR
from scibowl_qb import parse
from scibowl_qb import tags as tg
from scibowl_qb.convert import to_question
from scibowl_qb.extract import extract_round
from scibowl_qb.validate import validate_question_set

TOPICS = """\
disciplines:
  biology: Biology
  chemistry: Chemistry
topics:
  biology:
    cells: Cells
  chemistry:
    atoms: Atoms
"""


def make_dir(tmp_path, set_text=None, topics=TOPICS):
    (tmp_path / "topics.yaml").write_text(textwrap.dedent(topics), encoding="utf-8")
    if set_text is not None:
        (tmp_path / "ms").mkdir(exist_ok=True)
        (tmp_path / "ms" / "set15.yaml").write_text(textwrap.dedent(set_text), encoding="utf-8")
    return tmp_path


def question(qid="ms-set15-set-1-ms-2021-q01-tossup", set_name="set15"):
    return {"id": qid, "source": {"level": "ms", "set": set_name},
            "tags": {"disciplines": [], "topics": [], "source": None, "reviewed": False}}


def test_repo_topic_list_and_set15_load():
    loaded = tg.load()
    disciplines = set(loaded.topic_list.disciplines)
    assert disciplines == {"biology", "chemistry", "physics", "earth_and_space", "energy", "math"}
    assert {d for d, _ in loaded.topic_list.topics.values()} == disciplines
    set15 = loaded.sets[("ms", "set15")]
    assert len(set15.questions) == 300
    assert set15.source == "ai" and set15.reviewed is False


def test_disciplines_come_from_topics(tmp_path):
    tags = tg.load(make_dir(tmp_path, "questions:\n  ms-set15-set-1-ms-2021-q01-tossup: [atoms, cells]\n"))
    q = tg.apply(question(), tags)
    assert q["tags"] == {"disciplines": ["chemistry", "biology"], "topics": ["atoms", "cells"], "source": "ai", "reviewed": False}


def test_sets_without_a_tags_file_are_left_alone(tmp_path):
    tags = tg.load(make_dir(tmp_path, "questions:\n  ms-set15-set-1-ms-2021-q01-tossup: [atoms]\n"))
    q = tg.apply(question("ms-set01-m-round01-q01-tossup", "set01"), tags)
    assert q["tags"]["topics"] == []


def test_unknown_topic_stops(tmp_path):
    with pytest.raises(tg.TagsError, match="not in the topic list"):
        tg.load(make_dir(tmp_path, "questions:\n  ms-set15-set-1-ms-2021-q01-tossup: [momentum]\n"))


def test_question_from_another_set_stops(tmp_path):
    with pytest.raises(tg.TagsError, match="not a question of ms/set15"):
        tg.load(make_dir(tmp_path, "questions:\n  ms-set14-x-q01-tossup: [atoms]\n"))


def test_empty_topics_stop(tmp_path):
    with pytest.raises(tg.TagsError, match="at least one topic"):
        tg.load(make_dir(tmp_path, "questions:\n  ms-set15-set-1-ms-2021-q01-tossup: []\n"))


def test_topic_under_unknown_discipline_stops(tmp_path):
    with pytest.raises(tg.TagsError, match="unknown discipline"):
        tg.load(make_dir(tmp_path, topics="disciplines:\n  math: Math\ntopics:\n  physics:\n    waves: Waves\n"))


def test_untagged_question_in_a_tagged_set_stops(tmp_path):
    tags = tg.load(make_dir(tmp_path, "questions:\n  ms-set15-set-1-ms-2021-q01-tossup: [atoms]\n"))
    with pytest.raises(tg.TagsError, match="has no tags"):
        tg.apply(question("ms-set15-set-1-ms-2021-q01-bonus"), tags)


def test_reviewed_and_human_tags(tmp_path):
    tags = tg.load(make_dir(tmp_path, "tagged_by: human\nreviewed: true\nquestions:\n  ms-set15-set-1-ms-2021-q01-tossup: atoms\n"))
    q = tg.apply(question(), tags)
    assert q["tags"]["source"] == "human" and q["tags"]["reviewed"] is True and q["tags"]["topics"] == ["atoms"]


def test_set15_round_1_parses_with_valid_tags():
    tags = tg.load()
    questions = [tg.apply(to_question(rq), tags) for rq in extract_round(RAW_DIR / "ms/set15/Set-1-MS-2021.pdf", RAW_DIR)]
    assert len(questions) == 30
    assert all(q["tags"]["topics"] and q["tags"]["disciplines"] for q in questions)
    assert validate_question_set({"schema_version": 1, "generator": "test", "questions": questions}) == []
    first = next(q for q in questions if q["id"] == "ms-set15-set-1-ms-2021-q01-tossup")
    assert first["tags"]["disciplines"] == ["chemistry"]


def test_parse_stops_on_a_tag_for_a_missing_question(tmp_path):
    tags_dir = tmp_path / "tags"
    shutil.copytree(tg.DEFAULT_DIR, tags_dir)
    path = tags_dir / "ms" / "set15.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  ms-set15-set-1-ms-2021-q99-tossup: [atoms]\n", encoding="utf-8")
    code = parse.main(["--level", "ms", "--set", "set15", "--round", "Set-1-MS-2021", "--no-images",
                       "--out", str(tmp_path / "out"), "--tags", str(tags_dir)])
    assert code == 1


def test_review_page_lists_every_question():
    from scibowl_qb.tag_review import build
    tags = tg.load()
    questions = [tg.apply(to_question(rq), tags) for rq in extract_round(RAW_DIR / "ms/set15/Set-1-MS-2021.pdf", RAW_DIR)]
    page = build(questions, tags.topic_list, "Topic tags: test")
    assert page.count('<div class="q"') == sum(len(q["tags"]["topics"]) for q in questions)
    assert "Printed subject to discipline" in page
