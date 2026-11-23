# Science Bowl Question Bank

Parses National Science Bowl practice PDFs (published by the U.S. Department of Energy) into a clean, versioned question dataset for [Science Bowl Prep Lab](https://github.com/EchoPositiveX/scibowl-prep-lab).

See `ROADMAP.md` for what is planned.

## Layout

| Path | What it holds |
| --- | --- |
| `data/raw/` | Source PDFs, unchanged (see `data/raw/README.md`) |
| `src/scibowl_qb/` | The parser package |
| `corrections.yaml` | Fixes for problems in the source PDFs, each with a reason |
| `transcriptions/` | Text and LaTeX read from the images for questions the parser gets wrong (QB-10); see `transcriptions/README.md` |
| `tests/` | Tests (`pytest`) |
| `docs/decisions.md` | Decisions made so far |
| `ROADMAP.md` | To-do and nice-to-have lists |
| `CLAUDE.md` | How AI sessions should work in this repo |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Parsing

```bash
python -m scibowl_qb.parse --set set01 --round m_round01   # one round
python -m scibowl_qb.parse --set set01                     # one set
python -m scibowl_qb.parse --jobs 4                        # everything with images, 4 PDFs at a time
python -m scibowl_qb.parse --no-images --jobs 4            # text only, under a minute for all sets
python -m scibowl_qb.validate output/questions.json        # check a file against the format
python -m scibowl_qb.checks output/questions.json          # content checks (missing answers, footers, ...)
```

Output goes to `output/` (not committed): one JSON file per round under `output/rounds/`, everything combined in `output/questions.json`, and images under `output/images/`.

## Releases

The website downloads the dataset from this repo's GitHub Releases. A release has three files:

| File | What it holds |
| --- | --- |
| `questions.json` | Every question in the published format (`docs/question-format.md`) |
| `images.zip` | Question, answer and whole-question PNGs; paths start with `images/`, matching each question's `images` fields |
| `manifest.json` | Dataset version, counts per set, how many questions need review, and SHA-256 checksums |

Before a real release, try it out. On GitHub: **Actions > Release > Run workflow**, leave **version** empty and pick a set (for example `set16`). It builds just that set, publishes nothing, and attaches a download with `preview.html`: every question's parsed text next to its PDF image, with flagged questions highlighted. Releases also include `preview.html`.

To publish one: **Actions > Release > Run workflow** on `main`, with **version** filled in (for example `v1.0.0`). Or push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Either way, the **Release** workflow parses everything with images, validates, checks the question count per set, runs the content checks, and creates the GitHub Release (and its tag) only if all of them pass.

To build the same files locally without publishing anything:

```bash
python -m scibowl_qb.release 1.0.0 --jobs 4          # writes dist/
python -m scibowl_qb.release 0.0.1 --set set16 --trial   # quick try on one set; open dist/preview.html
```

Versions: bump the major number when the question format (`schema_version`) changes, the minor number when questions are added or fixed, and the patch number for small corrections.
