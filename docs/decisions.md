# Decisions

Newest first. Each entry: date, decision, and why if it isn't obvious.

## 2026-11-23: Set 16 (QB-24)

- Set 16 is the nine 2022 middle school rounds John downloaded. From 2022 the middle school rounds use six subjects (Biology, Chemistry, Earth and Space, Energy, Math, Physics) and 18 toss-ups per round, so `biology`, `chemistry` and `physics` are middle school categories too, not only high school ones.

## 2026-11-23: Set 15 round 7 (QB-23)

- `ms/set15/Set-7-HS-2021.pdf` was the high school round. John supplied the middle school version, `Set-7-MS-2021.pdf`, and it replaced the high school file. Set 15 is now 300 questions (10 rounds of 30).

## 2026-11-23: Subjects and question style (QB-07)

- Earth Science and every Earth and Space variant map to `earth_and_space`. The printed label stays in `category_raw`.
- The few high school labels (Biology, Chemistry, Physics) map to their own high school categories rather than being forced into middle school ones.
- A question that prints all four choices W) to Z) is multiple choice, even if its label says Short Answer. The printed label used to be ignored when it followed a dash ("Earth & Space – Multiple Choice"), and the style was guessed; now it is read.
- A question with no printed subject keeps its words as question text, and gets its subject from `corrections.yaml`.

## 2026-11-23: Question format v1 (QB-01)

- One JSON file holds a list of questions under `schema_version: 1`; see `docs/question-format.md`.
- Question IDs are derived from level, set, round, number and part, so they stay stable across re-parses.
- Every text field has a plain `text` and an optional `latex`; images are always kept as the fallback.
- Answers keep the printed `raw` text and split out `accept`, `do_not_accept` and `pronunciation`.
- `quality.text_status` (images_only, auto, verified) tells the website when it can trust the text.

## 2026-11-23: Initial plan

- Two repos: `scibowl-question-bank` (this one) and `scibowl-prep-lab` (website). The old `nsb` repo is kept as is, for reference.
- Middle school only for now; high school later.
- DOE question text may be shown publicly on the website.
- First rebuild and improve the pdfplumber parser on a new structure. Only after that, use an AI vision model to produce text with LaTeX, one or two sets at a time with review.
- Topic tagging will be AI-based; the topic list is generated later.
- Images stay as the fallback whenever text isn't verified.
