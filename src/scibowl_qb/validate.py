"""Validate question-set JSON files against the question format.

Usage:
    python -m scibowl_qb.validate FILE [FILE ...]

Checks the JSON Schema, then rules a schema can't express (unique IDs,
IDs matching their source, multiple choice answers naming a choice).
Exits with status 1 if any file has problems.
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_VERSION = 1


@lru_cache(maxsize=1)
def load_schema() -> dict:
    text = resources.files("scibowl_qb").joinpath("schema/question-set.schema.json").read_text(encoding="utf-8")
    return json.loads(text)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def expected_id(q: dict) -> str:
    src = q["source"]
    return f"{src['level']}-{src['set']}-{slugify(src['round'])}-q{q['number']:02d}-{q['part']}"


def validate_question_set(data: dict) -> list[str]:
    """Return a list of human-readable problems; empty means valid."""
    validator = Draft202012Validator(load_schema())
    problems = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in err.absolute_path) or "(root)"
        problems.append(f"{where}: {err.message}")
    if problems:
        return problems

    seen: set[str] = set()
    for i, q in enumerate(data["questions"]):
        qid = q["id"]
        if qid in seen:
            problems.append(f"questions/{i}: duplicate id {qid}")
        seen.add(qid)

        if qid != expected_id(q):
            problems.append(f"questions/{i}: id {qid} does not match its source (expected {expected_id(q)})")

        is_mc = q["format"] == "multiple_choice"
        if is_mc and q["choices"] is None:
            problems.append(f"questions/{i} ({qid}): multiple choice question has no choices")
        if not is_mc and q["choices"] is not None:
            problems.append(f"questions/{i} ({qid}): short answer question has choices")
        if is_mc and "choice" not in q["answer"]:
            problems.append(f"questions/{i} ({qid}): multiple choice answer has no choice letter")

        if q["quality"]["text_status"] == "images_only" and not q["images"]["question"]:
            problems.append(f"questions/{i} ({qid}): text_status is images_only but there is no question image")

    return problems


def main(argv: list[str] | None = None) -> int:
    paths = [Path(p) for p in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print(__doc__.strip())
        return 2

    failed = False
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"{path}: cannot read: {exc}")
            failed = True
            continue

        problems = validate_question_set(data)
        if problems:
            failed = True
            print(f"{path}: {len(problems)} problem(s)")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"{path}: OK ({len(data['questions'])} questions)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
