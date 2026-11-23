# Science Bowl Question Bank

Parses National Science Bowl practice PDFs (published by the U.S. Department of Energy) into a clean, versioned question dataset for [Science Bowl Prep Lab](https://github.com/EchoPositiveX/scibowl-prep-lab).

See `ROADMAP.md` for what is planned.

## Layout

| Path | What it holds |
| --- | --- |
| `data/raw/` | Source PDFs, unchanged (see `data/raw/README.md`) |
| `src/scibowl_qb/` | The parser package |
| `corrections.yaml` | Fixes for problems in the source PDFs, each with a reason |
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
python -m scibowl_qb.parse                                 # everything (slow with images)
python -m scibowl_qb.parse --no-images                     # text only, about 2 minutes for all sets
python -m scibowl_qb.validate output/questions.json        # check a file against the format
```

Output goes to `output/` (not committed): one JSON file per round under `output/rounds/`, everything combined in `output/questions.json`, and images under `output/images/`.
