# Working in this repo

This repo turns National Science Bowl PDFs into a clean, versioned question dataset. The website (`scibowl-prep-lab`) only reads the published dataset, so the question format in `docs/` is a contract: change it deliberately and bump `schema_version`.

## How to pick up work

1. Read `ROADMAP.md`. Work only on items in **Now**, one or two at a time, unless John asks for something else.
2. Read `docs/decisions.md` before proposing changes to scope or approach. Do not re-ask questions answered there.
3. Create a branch per item, named like `qb-02-port-parser`. Never commit directly to `main`.
4. Open a pull request that names the roadmap ID(s) in its title, e.g. `QB-02: Port the parser`.
5. In the same pull request, move the item to **Done** in `ROADMAP.md` with a one-line note. Add any new ideas you noticed to **Nice to have**.
6. If a choice changes the plan, record it in `docs/decisions.md`.

## Ground rules

- Middle school only for now (`data/raw/ms`). High school is a later item.
- Keep raw PDFs unchanged. Fix bad source data with the corrections file, not by editing PDFs.
- Generated output goes to `output/` (git-ignored) and is published as releases, not committed.
- Every parser change must keep the tests passing. A full parse is slow, so tests should be able to run on a single set or round.
- Run AI-based steps (LaTeX, tagging) on one or two sets at a time, and stop for John to review results before going further.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```
