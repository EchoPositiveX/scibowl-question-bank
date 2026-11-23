"""Build a dataset release (QB-09).

Usage:
    python -m scibowl_qb.release 1.0.0 --jobs 4

Parses every PDF with images into a clean build folder, validates the result,
runs the content checks, and writes to dist/:

    questions.json   every question, in the published format
    images.zip       question, answer and whole-question PNGs (paths start with images/)
    manifest.json    dataset version, counts per set, needs-review count, file checksums

Nothing is published. The GitHub workflow (.github/workflows/release.yml) runs this
when a version tag like v1.0.0 is pushed, then uploads dist/ as a GitHub Release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

from . import REPO_ROOT, __version__
from . import checks
from . import parse
from .validate import SCHEMA_VERSION

log = logging.getLogger("scibowl_qb.release")

VERSION = re.compile(r"^v?(\d+\.\d+\.\d+)$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_images(images_dir: Path, out_zip: Path) -> int:
    files = sorted(p for p in images_dir.rglob("*.png"))
    # PNGs are already compressed, so store them as they are.
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in files:
            zf.write(p, ("images" / p.relative_to(images_dir)).as_posix())
    return len(files)


def build_manifest(version: str, data: dict, files: dict[str, Path], image_count: int) -> dict:
    questions = data["questions"]
    by_set = Counter(f"{q['source']['level']}/{q['source']['set']}" for q in questions)
    review = sum("needs_review" in q["quality"]["flags"] for q in questions)
    return {
        "dataset_version": version,
        "schema_version": SCHEMA_VERSION,
        "generator": f"scibowl-qb {__version__}",
        "generated_at": data.get("generated_at"),
        "question_count": len(questions),
        "needs_review_count": review,
        "image_count": image_count,
        "sets": dict(sorted(by_set.items())),
        "files": {name: {"bytes": p.stat().st_size, "sha256": sha256(p)} for name, p in files.items()},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build a dataset release into dist/ (nothing is published).")
    ap.add_argument("version", help="dataset version, e.g. 1.0.0 or v1.0.0")
    ap.add_argument("--build", type=Path, default=REPO_ROOT / "build" / "release", help="scratch folder, emptied first")
    ap.add_argument("--dist", type=Path, default=REPO_ROOT / "dist")
    ap.add_argument("-j", "--jobs", type=int, default=1)
    ap.add_argument("--level", help="limit to one level (for trying the release out)")
    ap.add_argument("--set", dest="set_name", help="limit to one set (for trying the release out)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    m = VERSION.match(args.version)
    if not m:
        log.error("Version must look like 1.0.0 (got %r)", args.version)
        return 2
    version = m.group(1)

    for folder in (args.build, args.dist):
        shutil.rmtree(folder, ignore_errors=True)
    args.dist.mkdir(parents=True)

    parse_args = ["--out", str(args.build), "--jobs", str(args.jobs)]
    if args.level:
        parse_args += ["--level", args.level]
    if args.set_name:
        parse_args += ["--set", args.set_name]
    if parse.main(parse_args) != 0:
        log.error("Parse or validation failed; no release built")
        return 1

    combined = args.build / "questions.json"
    data = json.loads(combined.read_text(encoding="utf-8"))
    findings = checks.run_checks(data["questions"])
    print(checks.report(findings))
    if any(not f.flagged for f in findings):
        log.error("Content checks found unflagged problems; no release built")
        return 1

    files = {"questions.json": args.dist / "questions.json", "images.zip": args.dist / "images.zip"}
    shutil.copyfile(combined, files["questions.json"])
    image_count = zip_images(args.build / "images", files["images.zip"])
    manifest = build_manifest(version, data, files, image_count)
    (args.dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nRelease {version}: {manifest['question_count']} questions, {image_count} images, "
          f"{manifest['needs_review_count']} need review. Files in {args.dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
