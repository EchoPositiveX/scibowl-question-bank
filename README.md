# Science Bowl Question Bank

Parses National Science Bowl practice PDFs (published by the U.S. Department of Energy) into a clean, versioned question dataset for [Science Bowl Prep Lab](https://github.com/EchoPositiveX/scibowl-prep-lab).

See `ROADMAP.md` for what is planned.

## Layout

| Path | What it holds |
| --- | --- |
| `data/raw/` | Source PDFs, unchanged (see `data/raw/README.md`) |
| `src/scibowl_qb/` | The parser package |
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
