"""Text and LaTeX transcribed from the question images (QB-10).

Files live in transcriptions/<level>/<set>.yaml. See transcriptions/README.md for the format.
An entry replaces the parsed text of one question. Until a person sets `reviewed: true`,
the question stays `images_only` and flagged `needs_review`, so the website keeps showing
the printed images; after review it becomes `verified` and the website can show the LaTeX.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import REPO_ROOT

log = logging.getLogger(__name__)

DEFAULT_DIR = REPO_ROOT / "transcriptions"
CHOICE_LETTERS = ("W", "X", "Y", "Z")
NOTE_UNREVIEWED = "Text and LaTeX transcribed from the question image (QB-10); not reviewed yet, so the images are still shown"
NOTE_REVIEWED = "Text and LaTeX transcribed from the question image (QB-10) and checked against it"


class TranscriptionError(ValueError):
    """A transcription file is malformed or refers to a question that doesn't exist."""


@dataclass
class Transcription:
    id: str
    question: dict
    answer: dict
    choices: dict | None
    reviewed: bool
    file: Path
    used: int = 0


def _text_field(value, where: str, extra_keys: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise TranscriptionError(f"{where}: must have text and latex")
    unknown = set(value) - {"text", "latex"} - extra_keys
    if unknown:
        raise TranscriptionError(f"{where}: unknown keys {sorted(unknown)}")
    for key in ("text", "latex"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise TranscriptionError(f"{where}: '{key}' must be a non-empty string")
    if value["latex"].replace("\\$", "").count("$") % 2:
        raise TranscriptionError(f"{where}: latex has an unmatched $")
    return value


def load_file(path: Path) -> list[Transcription]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    unknown = set(data) - {"source", "questions"}
    if unknown:
        raise TranscriptionError(f"{path}: unknown top-level keys {sorted(unknown)}")
    result = []
    for i, entry in enumerate(data.get("questions") or []):
        where = f"{path} questions[{i}]"
        extra = set(entry) - {"id", "question", "answer", "choices", "reviewed"}
        if extra:
            raise TranscriptionError(f"{where}: unknown keys {sorted(extra)}")
        if not isinstance(entry.get("id"), str):
            raise TranscriptionError(f"{where}: missing 'id'")
        where = f"{path} {entry['id']}"
        question = _text_field(entry.get("question"), f"{where} question")
        answer = _text_field(entry.get("answer"), f"{where} answer", {"accept"})
        if "accept" in answer and not (isinstance(answer["accept"], list) and all(isinstance(a, str) for a in answer["accept"])):
            raise TranscriptionError(f"{where} answer: 'accept' must be a list of strings")
        choices = entry.get("choices")
        if choices is not None:
            if not isinstance(choices, dict) or set(choices) != set(CHOICE_LETTERS):
                raise TranscriptionError(f"{where}: choices must have exactly W, X, Y and Z")
            choices = {k: _text_field(v, f"{where} choices.{k}") for k, v in choices.items()}
        if not isinstance(entry.get("reviewed"), bool):
            raise TranscriptionError(f"{where}: 'reviewed' must be true or false")
        result.append(Transcription(entry["id"], question, answer, choices, entry["reviewed"], Path(path)))
    return result


def load(directory: Path = DEFAULT_DIR) -> dict[str, Transcription]:
    """All transcriptions under directory, by question ID."""
    by_id: dict[str, Transcription] = {}
    for path in sorted(Path(directory).glob("*/*.yaml")):
        for t in load_file(path):
            if t.id in by_id:
                raise TranscriptionError(f"{t.id} is transcribed in both {by_id[t.id].file} and {path}")
            by_id[t.id] = t
    return by_id


def apply(question: dict, transcriptions: dict[str, Transcription]) -> dict:
    """Replace this question's text with its transcription, if there is one. Returns the question."""
    t = transcriptions.get(question["id"])
    if t is None:
        return question
    if (t.choices is None) != (question["choices"] is None):
        raise TranscriptionError(f"{t.id}: choices given for a short-answer question, or missing for multiple choice")
    question["question"]["text"] = t.question["text"]
    question["question"]["latex"] = t.question["latex"]
    if t.choices:
        for letter, c in t.choices.items():
            question["choices"][letter] = {"text": c["text"], "latex": c["latex"]}
    question["answer"]["text"] = t.answer["text"]
    question["answer"]["latex"] = t.answer["latex"]
    if t.answer.get("accept"):
        question["answer"]["accept"] = list(t.answer["accept"])
    elif "accept" in t.answer:
        question["answer"].pop("accept", None)
    t.used += 1

    quality = question["quality"]
    flags = set(quality["flags"])
    if any("$" in f["latex"] for f in [t.question, t.answer, *(t.choices or {}).values()]):
        flags.add("has_math")
    if t.reviewed:
        quality["text_status"] = "verified"
        flags.discard("needs_review")
        quality["notes"].append(NOTE_REVIEWED)
    else:
        # text_status stays as the parser set it: images_only whenever there are images.
        flags.add("needs_review")
        quality["notes"].append(NOTE_UNREVIEWED)
    quality["flags"] = sorted(flags)
    return question
