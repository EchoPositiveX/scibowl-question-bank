"""Topic tags (QB-11, QB-12).

tags/topics.yaml is the topic list: the six disciplines and the topics under each.
tags/<level>/<set>.yaml tags every question of one set with one or more topic IDs:

    source: Who or what made these, and when
    reviewed: false
    questions:
      ms-set15-set-1-ms-2021-q01-tossup: [atoms]

A question's `tags.disciplines` come from its topics, so they can't disagree. A tags file
must cover every question in its set, and every ID must match a question, or the parse stops.
`tags.source` is "ai" and `tags.reviewed` follows the file's `reviewed` until John checks it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import REPO_ROOT

DEFAULT_DIR = REPO_ROOT / "tags"
SOURCES = ("ai", "human")


class TagsError(ValueError):
    """A tags file is malformed or doesn't match the questions."""


@dataclass
class TopicList:
    disciplines: dict[str, str]          # id -> label
    topics: dict[str, tuple[str, str]]   # id -> (discipline id, label)


@dataclass
class SetTags:
    level: str
    set: str
    source: str
    reviewed: bool
    questions: dict[str, list[str]]
    file: Path
    used: set[str] = field(default_factory=set)


@dataclass
class Tags:
    topic_list: TopicList | None = None
    sets: dict[tuple[str, str], SetTags] = field(default_factory=dict)


def load_topics(path: Path) -> TopicList:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    disciplines = data.get("disciplines")
    if not isinstance(disciplines, dict) or not disciplines:
        raise TagsError(f"{path}: 'disciplines' must map discipline IDs to labels")
    topics: dict[str, tuple[str, str]] = {}
    for discipline, entries in (data.get("topics") or {}).items():
        if discipline not in disciplines:
            raise TagsError(f"{path}: topics listed under unknown discipline '{discipline}'")
        for topic, label in (entries or {}).items():
            if topic in topics:
                raise TagsError(f"{path}: topic '{topic}' is listed twice")
            if topic in disciplines:
                raise TagsError(f"{path}: topic '{topic}' has the same ID as a discipline")
            topics[topic] = (discipline, str(label))
    return TopicList({k: str(v) for k, v in disciplines.items()}, topics)


def load_set(path: Path, topic_list: TopicList) -> SetTags:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    unknown = set(data) - {"source", "tagged_by", "reviewed", "questions"}
    if unknown:
        raise TagsError(f"{path}: unknown top-level keys {sorted(unknown)}")
    tagged_by = data.get("tagged_by", "ai")
    if tagged_by not in SOURCES:
        raise TagsError(f"{path}: 'tagged_by' must be one of {SOURCES}")
    if not isinstance(data.get("reviewed", False), bool):
        raise TagsError(f"{path}: 'reviewed' must be true or false")
    level, set_name = path.parent.name, path.stem
    prefix = f"{level}-{set_name}-"
    questions = {}
    for qid, topics in (data.get("questions") or {}).items():
        if not str(qid).startswith(prefix):
            raise TagsError(f"{path}: {qid} is not a question of {level}/{set_name}")
        if isinstance(topics, str):
            topics = [topics]
        if not isinstance(topics, list) or not topics:
            raise TagsError(f"{path}: {qid} needs at least one topic")
        unknown_topics = [t for t in topics if t not in topic_list.topics]
        if unknown_topics:
            raise TagsError(f"{path}: {qid} has topics not in the topic list: {unknown_topics}")
        if len(set(topics)) != len(topics):
            raise TagsError(f"{path}: {qid} lists a topic twice")
        questions[qid] = list(topics)
    return SetTags(level, set_name, tagged_by, data.get("reviewed", False), questions, path)


def load(directory: Path = DEFAULT_DIR) -> Tags:
    """The topic list and every set's tags under directory. A missing folder means no tags."""
    directory = Path(directory)
    topics_path = directory / "topics.yaml"
    if not topics_path.exists():
        return Tags()
    topic_list = load_topics(topics_path)
    sets = {}
    for path in sorted(directory.glob("*/*.yaml")):
        st = load_set(path, topic_list)
        sets[(st.level, st.set)] = st
    return Tags(topic_list, sets)


def apply(question: dict, tags: Tags | None) -> dict:
    """Fill in question["tags"] if its set has a tags file. Returns the question."""
    if tags is None:
        return question
    st = tags.sets.get((question["source"]["level"], question["source"]["set"]))
    if st is None:
        return question
    topics = st.questions.get(question["id"])
    if topics is None:
        raise TagsError(f"{st.file}: {question['id']} has no tags; a tags file must cover every question in its set")
    st.used.add(question["id"])
    disciplines = []
    for t in topics:
        d = tags.topic_list.topics[t][0]
        if d not in disciplines:
            disciplines.append(d)
    question["tags"] = {"disciplines": disciplines, "topics": list(topics), "source": st.source, "reviewed": st.reviewed}
    return question
