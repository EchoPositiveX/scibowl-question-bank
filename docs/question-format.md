# Question format (schema version 1)

This is the contract between the question bank and the website. The parser writes it; the website only reads it. The machine-readable version is [`src/scibowl_qb/schema/question-set.schema.json`](../src/scibowl_qb/schema/question-set.schema.json), and [`examples/sample-question-set.json`](../examples/sample-question-set.json) shows 10 real questions in this format.

Check a file with:

```bash
python -m scibowl_qb.validate path/to/file.json
```

Changing the format means bumping `schema_version` and recording why in `docs/decisions.md`. An optional new field that older readers can ignore doesn't need a bump, but is still recorded there.

## File

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-23T18:00:00Z",
  "generator": "scibowl-qb 0.2.0",
  "questions": [ ... ]
}
```

## One question

```json
{
  "id": "ms-set13-2019-nsb-msr-round-1a-q02-bonus",
  "source": { "level": "ms", "set": "set13", "round": "2019-NSB-MSR-Round-1A", "round_number": 1,
              "pdf": "ms/set13/2019-NSB-MSR-Round-1A.pdf", "page": 1 },
  "number": 2,
  "part": "bonus",
  "category": "earth_and_space",
  "category_raw": "Earth And Space",
  "format": "short_answer",
  "question": { "text": "Kepler's laws of planetary motion were empirically determined from data collected by what Danish astronomer?", "latex": null },
  "choices": null,
  "answer": { "text": "TYCHO BRAHE", "latex": null, "pronunciation": "TEE-koh BRAH-hay", "raw": "TYCHO BRAHE [TEE-koh BRAH-hay]" },
  "images": { "question": "images/ms/set13/2019-NSB-MSR-Round-1A/q02-bonus-question.png", "answer": "...", "entire": "..." },
  "tags": { "disciplines": [], "topics": [], "source": null, "reviewed": false },
  "quality": { "text_status": "auto", "flags": ["corrected"], "notes": ["Removed page footer from the answer"] }
}
```

## Fields

| Field | Meaning |
| --- | --- |
| `id` | Stable ID: `{level}-{set}-{round slug}-q{NN}-{part}`. The website keys user marks and notes on it, so it must not change when the parser improves. The validator checks it matches `source`, `number` and `part`. |
| `source` | Where the question came from. `pdf` is relative to `data/raw` with forward slashes. `round_number` is the round as an integer, or null if it can't be worked out. |
| `number` | Question number within the round. |
| `part` | `tossup` or `bonus`. |
| `category` | Normalized NSB category: `life_science`, `physical_science`, `earth_and_space`, `energy`, `math`, `general_science`, `biology`, `chemistry`, `physics`. Middle school rounds up to 2021 use the first six; from 2022 they use biology, chemistry, earth_and_space, energy, math and physics, like high school. Labels map as: Earth Science, Earth and Space, Earth & Space and Earth and Space Science → `earth_and_space`; Math and Mathematics → `math`; the rest by name. Null only for a label the parser doesn't know, and then the question is flagged `needs_review`. |
| `category_raw` | The subject as printed (title case), for traceability. |
| `format` | `short_answer` or `multiple_choice`. |
| `question` | `text` is cleaned plain text (no "Short Answer" prefix, no line breaks from the PDF layout). `latex` is the same with math as `$...$` and chemistry as `\ce{...}`, null until produced from `transcriptions/` (QB-10). |
| `choices` | For multiple choice, `W`, `X`, `Y`, `Z`, each with `text` and `latex`. Null for short answer. |
| `answer` | `text` is the main answer only. `choice` is the letter for multiple choice. `accept` and `do_not_accept` hold the moderator notes split out; `accept_latex` and `do_not_accept_latex` are the same with math as LaTeX, in the same order, once transcribed (QB-10). `pronunciation` holds bracketed hints. `raw` keeps the full printed answer. |
| `images` | Crops of the question, the answer, and the whole thing, relative to the release root. Kept even when text is verified. |
| `tags` | `topics` are IDs from `tags/topics.yaml` (QB-11), such as `genetics` or `motion-forces`. `disciplines` are the 2022 subjects those topics belong to (`biology`, `chemistry`, `physics`, `earth_and_space`, `energy`, `math`), plus the printed subject when it is one of those six (every Energy question, and every 2022 question). Empty until a set is tagged (see `tags/README.md`). `source` says who tagged it (`ai` or `human`); `reviewed` says whether John checked it. |
| `quality.text_status` | `images_only`: the text is unreliable, so show images. `auto`: parsed text, not checked. `verified`: text (and LaTeX if present) checked against the image. |
| `quality.flags` | `has_math`, `has_chemistry`, `has_figure`, `corrected`, `needs_review`. |
| `quality.notes` | What was corrected and why, in plain words. Entries from `corrections.yaml` start with "Corrected:". |

## What the website should do

- Show `question.latex` (rendered with KaTeX) if present and `text_status` is `verified`; otherwise `question.text` if `text_status` is `auto` or `verified`; otherwise the question image.
- In game mode, never send `answer` to the screen until the moderator reveals it.
- Use `id` for anything saved per question.

## Problems this format is designed to capture

Taken from the current parser's output:

- Answers that picked up page footers (`... Page 1`) or `~~~~` separators: cleaned in `answer.text`, original kept in `answer.raw`, explained in `quality.notes`.
- `GEOSTATIONARY (ACCEPT: ...; DO NOT ACCEPT ...)`: split into `accept` and `do_not_accept`.
- `2x2 + 7x + 3`, where the exponent was lost: marked `images_only` and `has_math` until LaTeX is produced and checked.
- Subjects like "Earth Science" and "Earth And Space Science": normalized in `category`, original kept in `category_raw`.
