"""Command line: parse NSB PDFs into the question format.

Examples:
    python -m scibowl_qb.parse                       # everything under data/raw
    python -m scibowl_qb.parse --set set01           # one set (all levels)
    python -m scibowl_qb.parse --set set13 --round 2019-NSB-MSR-Round-1A
    python -m scibowl_qb.parse --set set01 --no-images   # much faster, text only

Writes:
    output/rounds/{level}/{set}/{round}.json   one file per round
    output/questions.json                      every round found under output/rounds, combined
    output/images/...                          question, answer and whole-question PNGs
and prints a count summary compared with the expected numbers per set.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import RAW_DIR, REPO_ROOT, __version__
from . import corrections as corr
from . import transcriptions as tr
from .convert import to_question, to_question_set
from .extract import extract_round
from .validate import slugify, validate_question_set

log = logging.getLogger("scibowl_qb.parse")

# Expected question counts per middle school set, from the old repo's checks.
EXPECTED_MS_SET_COUNTS = {
    "set01": 900, "set02": 500, "set03": 750, "set04": 850, "set05": 800,
    "set06": 850, "set07": 750, "set08": 782, "set09": 782, "set10": 782,
    "set11": 782, "set12": 782, "set13": 982, "set14": 782, "set15": 300, "set16": 324,
}

# Questions the parser is known not to find yet (counted as found when checking a release).
KNOWN_MISSING = {"set02": 1, "set03": 2, "set04": 3}


def count_problems(questions: list[dict]) -> list[str]:
    """Sets whose question count doesn't match the expected count (allowing for KNOWN_MISSING)."""
    by_set = Counter((q["source"]["level"], q["source"]["set"]) for q in questions)
    problems = []
    for (level, s), found in sorted(by_set.items()):
        expected = EXPECTED_MS_SET_COUNTS.get(s) if level == "ms" else None
        if expected is None:
            problems.append(f"{level}/{s}: no expected count (add it to EXPECTED_MS_SET_COUNTS)")
        elif found + KNOWN_MISSING.get(s, 0) != expected:
            problems.append(f"{level}/{s}: found {found}, expected {expected - KNOWN_MISSING.get(s, 0)}")
    return problems


GENERATOR = f"scibowl-qb {__version__}"


def find_pdfs(raw_dir: Path, level: str | None, set_name: str | None, round_name: str | None) -> list[Path]:
    pattern = f"{level or '*'}/{set_name or '*'}/{round_name or '*'}.pdf"
    return sorted(raw_dir.glob(pattern))


def parse_one(pdf: Path, raw_dir: Path, out_dir: Path, images: bool, corrections: corr.Corrections,
              transcriptions: dict[str, tr.Transcription] | None = None) -> tuple[Path, list[dict]]:
    """Parse one PDF, apply corrections and transcriptions, and write its round file."""
    rel = pdf.relative_to(raw_dir)
    raw = extract_round(pdf, raw_dir, images_dir=out_dir / "images" if images else None, corrections=corrections)
    questions = [tr.apply(corr.apply_question_corrections(to_question(rq), corrections), transcriptions or {}) for rq in raw]
    round_file = out_dir / "rounds" / rel.with_suffix(".json")
    round_file.parent.mkdir(parents=True, exist_ok=True)
    round_file.write_text(json.dumps(to_question_set(questions, GENERATOR), indent=2, ensure_ascii=False), encoding="utf-8")
    return round_file, questions


def _parse_one_in_worker(args) -> tuple[Path, list[dict]]:
    pdf, raw_dir, out_dir, images, corrections_path, transcriptions_dir = args
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    return parse_one(pdf, raw_dir, out_dir, images, corr.load(corrections_path), tr.load(transcriptions_dir))


def parse_pdfs(
    pdfs: list[Path], raw_dir: Path, out_dir: Path, images: bool, corrections: corr.Corrections,
    jobs: int = 1, corrections_path: Path | None = None, transcriptions_dir: Path | None = None,
) -> dict[Path, list[dict]]:
    """Parse each PDF and return {round file: questions}. With jobs > 1, PDFs are parsed in parallel."""
    written = {}
    transcriptions_dir = transcriptions_dir or tr.DEFAULT_DIR
    if jobs <= 1:
        transcriptions = tr.load(transcriptions_dir)
        for n, pdf in enumerate(pdfs, 1):
            log.info("[%d/%d] %s", n, len(pdfs), pdf.relative_to(raw_dir).as_posix())
            round_file, questions = parse_one(pdf, raw_dir, out_dir, images, corrections, transcriptions)
            written[round_file] = questions
        return written

    work = [(pdf, raw_dir, out_dir, images, corrections_path or corr.DEFAULT_PATH, transcriptions_dir) for pdf in pdfs]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for n, (round_file, questions) in enumerate(pool.map(_parse_one_in_worker, work), 1):
            log.info("[%d/%d] %s", n, len(pdfs), round_file.relative_to(out_dir / "rounds").as_posix())
            written[round_file] = questions
    return written


def combine_rounds(out_dir: Path) -> dict:
    questions = []
    for f in sorted((out_dir / "rounds").glob("*/*/*.json")):
        questions.extend(json.loads(f.read_text(encoding="utf-8"))["questions"])
    questions.sort(key=lambda q: (q["source"]["level"], q["source"]["set"], q["source"]["round_number"] or 0,
                                  q["source"]["round"], q["number"], q["part"] != "tossup"))
    return to_question_set(questions, GENERATOR, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def summarize(questions: list[dict]) -> str:
    by_set = Counter((q["source"]["level"], q["source"]["set"]) for q in questions)
    review = Counter((q["source"]["level"], q["source"]["set"]) for q in questions if "needs_review" in q["quality"]["flags"])
    lines = [f"{'set':<10}{'found':>7}{'expected':>10}{'missing':>9}{'needs review':>14}"]
    for (level, s), found in sorted(by_set.items()):
        expected = EXPECTED_MS_SET_COUNTS.get(s) if level == "ms" else None
        missing = "" if expected is None else expected - found
        lines.append(f"{level + '/' + s:<10}{found:>7}{expected or '':>10}{missing:>9}{review[(level, s)]:>14}")
    lines.append(f"{'total':<10}{len(questions):>7}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse NSB PDFs into the question format.")
    ap.add_argument("--level", help="e.g. ms")
    ap.add_argument("--set", dest="set_name", help="e.g. set01")
    ap.add_argument("--round", dest="round_name", help="round file name without .pdf, e.g. m_round01")
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "output")
    ap.add_argument("--corrections", type=Path, default=corr.DEFAULT_PATH)
    ap.add_argument("--transcriptions", type=Path, default=tr.DEFAULT_DIR, help="folder of transcriptions/<level>/<set>.yaml")
    ap.add_argument("--no-images", action="store_true", help="skip image cropping (much faster)")
    ap.add_argument("-j", "--jobs", type=int, default=1, help="PDFs to parse in parallel (e.g. the number of CPU cores)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("pdfminer").setLevel(logging.WARNING)

    pdfs = find_pdfs(args.raw_dir, args.level, args.set_name, args.round_name)
    if not pdfs:
        log.error("No PDFs matched under %s", args.raw_dir)
        return 1

    try:
        corrections = corr.load(args.corrections)
        transcriptions = tr.load(args.transcriptions)
    except (corr.CorrectionsError, tr.TranscriptionError) as exc:
        log.error("%s", exc)
        return 1

    try:
        written = parse_pdfs(pdfs, args.raw_dir, args.out, images=not args.no_images, corrections=corrections,
                             jobs=args.jobs, corrections_path=args.corrections, transcriptions_dir=args.transcriptions)
    except (corr.CorrectionsError, tr.TranscriptionError) as exc:
        log.error("%s", exc)
        return 1

    parsed_rounds = {f"{p.parent.parent.name}-{p.parent.name}-{slugify(p.stem)}-" for p in pdfs}
    parsed_ids = {q["id"] for questions in written.values() for q in questions}
    unused = [c for c in corrections.questions
              if any(c.id.startswith(r) for r in parsed_rounds) and c.id not in parsed_ids]
    unused += [t for t in transcriptions.values()
               if any(t.id.startswith(r) for r in parsed_rounds) and t.id not in parsed_ids]
    if unused:
        for c in unused:
            where = c.file if isinstance(c, tr.Transcription) else "corrections.yaml"
            log.error("%s: %s matched no question (check the ID)", where, c.id)
        return 1
    combined = combine_rounds(args.out)
    problems = validate_question_set(combined)
    (args.out / "questions.json").write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")

    print(summarize(combined["questions"]))
    if problems:
        print(f"\n{len(problems)} validation problem(s), first 20:")
        for p in problems[:20]:
            print(f"  - {p}")
        return 1
    print(f"\nWrote {len(combined['questions'])} questions to {args.out / 'questions.json'} (valid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
