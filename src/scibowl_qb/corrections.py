"""Load and apply corrections.yaml (QB-04).

See the comments at the top of corrections.yaml for the file format.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import REPO_ROOT

log = logging.getLogger(__name__)

DEFAULT_PATH = REPO_ROOT / "corrections.yaml"
EXTRACT_MATCH_KEYS = {"level", "set", "round", "page", "number", "part", "subject_raw", "style"}
EXTRACT_SET_KEYS = {"number", "part", "subject_raw", "style"}


class CorrectionsError(ValueError):
    """corrections.yaml is malformed or refers to something that doesn't exist."""


@dataclass
class ExtractCorrection:
    match: dict
    set: dict
    reason: str
    question_starts_with: str | None = None
    used: int = 0


@dataclass
class QuestionCorrection:
    id: str
    set: dict
    reason: str
    used: int = 0


@dataclass
class Corrections:
    extract: list[ExtractCorrection] = field(default_factory=list)
    questions: list[QuestionCorrection] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "Corrections":
        return cls()

    def unused_question_corrections(self) -> list[QuestionCorrection]:
        return [c for c in self.questions if c.used == 0]


def _require(entry: dict, key: str, where: str):
    if key not in entry:
        raise CorrectionsError(f"{where}: missing '{key}'")
    return entry[key]


def load(path: Path = DEFAULT_PATH) -> Corrections:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    unknown = set(data) - {"extract", "questions"}
    if unknown:
        raise CorrectionsError(f"{path}: unknown top-level keys {sorted(unknown)}")

    result = Corrections()
    for i, entry in enumerate(data.get("extract") or []):
        where = f"{path} extract[{i}]"
        extra = set(entry) - {"match", "set", "reason", "question_starts_with"}
        if extra:
            raise CorrectionsError(f"{where}: unknown keys {sorted(extra)}")
        match, values, reason = (_require(entry, k, where) for k in ("match", "set", "reason"))
        if set(match) - EXTRACT_MATCH_KEYS:
            raise CorrectionsError(f"{where}: can't match on {sorted(set(match) - EXTRACT_MATCH_KEYS)}")
        if set(values) - EXTRACT_SET_KEYS:
            raise CorrectionsError(f"{where}: can't set {sorted(set(values) - EXTRACT_SET_KEYS)}")
        result.extract.append(ExtractCorrection(match, values, str(reason).strip(), entry.get("question_starts_with")))

    seen_ids = set()
    for i, entry in enumerate(data.get("questions") or []):
        where = f"{path} questions[{i}]"
        extra = set(entry) - {"id", "set", "reason"}
        if extra:
            raise CorrectionsError(f"{where}: unknown keys {sorted(extra)}")
        qid, values, reason = (_require(entry, k, where) for k in ("id", "set", "reason"))
        if qid in seen_ids:
            raise CorrectionsError(f"{where}: {qid} is corrected more than once; combine the entries")
        seen_ids.add(qid)
        result.questions.append(QuestionCorrection(qid, values, str(reason).strip()))
    return result


def apply_extract_corrections(rq, corrections: Corrections) -> None:
    """Apply matching extract corrections to a RawQuestion in place."""
    for c in corrections.extract:
        if any(getattr(rq, k) != v for k, v in c.match.items()):
            continue
        if c.question_starts_with and not "\n".join(rq.question_lines).startswith(c.question_starts_with):
            continue
        for key, value in c.set.items():
            setattr(rq, key, value)
        c.used += 1
        rq.overrides_applied.append(f"Corrected: {c.reason}")
        log.info("Correction applied to %s/%s/%s: %s", rq.set, rq.round, rq.number, c.reason)


def _set_path(obj: dict, dotted: str, value, qid: str) -> None:
    keys = dotted.split(".")
    target = obj
    for k in keys[:-1]:
        if not isinstance(target, dict) or k not in target or target[k] is None:
            raise CorrectionsError(f"{qid}: can't set {dotted}: '{k}' doesn't exist on this question")
        target = target[k]
    target[keys[-1]] = value


def apply_question_corrections(question: dict, corrections: Corrections) -> dict:
    """Apply the correction for this question's ID, if any. Returns the question."""
    for c in corrections.questions:
        if c.id != question["id"]:
            continue
        for path, value in c.set.items():
            if path == "id" or path.startswith("source."):
                raise CorrectionsError(f"{c.id}: change IDs and sources with an extract correction instead")
            _set_path(question, path, value, c.id)
        c.used += 1
        quality = question["quality"]
        quality["notes"].append(f"Corrected: {c.reason}")
        quality["flags"] = sorted(set(quality["flags"]) | {"corrected"})
    return question
