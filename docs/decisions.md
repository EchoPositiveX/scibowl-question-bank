# Decisions

Newest first. Each entry: date, decision, and why if it isn't obvious.

## 2026-11-24: When an ACCEPT is split into several answers (QB-32)

- A printed ACCEPT is split only on a lower case "or" (the older sets use it between upper case answers, "D-GLUCOSE or DEXTROSE"), and only when the entry has no comma, no lower case "for" and doesn't start with a sign ("+ or -").
- Commas are split only when every part is a number with the same value ("6 18/25, 6.72"). Other commas and upper case OR are left alone, because they are usually part of one answer ("1, 2, AND 4", "Y OR ORDINATE AXIS").
- Printed "(Solution: ...)" working is dropped from `answer.text` and kept in `answer.raw`. Publishing it as its own field is QB-33.

## 2026-11-24: Transcriptions restore multiple choice (QB-10)

- When the parser can't read a multiple choice question's four choices or its answer letter, it makes the question short answer. In set 06 that happened to 17 of the 62 flagged questions.
- A transcription may now give the choices and `answer.choice` for such a question. That makes it `multiple_choice` again and adds a note saying so. The reverse (leaving out the choices of a question the parser read as multiple choice) still stops the parse.
- This changes no field in the question format, so schema_version stays 1.

## 2026-11-23: Transcriptions for unreadable math (QB-10)

- Text and LaTeX for questions the parser can't read go in `transcriptions/<level>/<set>.yaml`, one file per set, applied after `corrections.yaml`. They are data files a person can review and edit, like corrections, not parser code.
- An entry changes nothing the website shows until it is marked `reviewed: true`: until then the question stays flagged `needs_review` and the images are shown. Reviewed entries become `verified`.
- The first batch (set 01, 28 questions) was transcribed by Claude reading the question images directly in a session, so no API key or spending was needed. Running the rest through an API (QB-31) waits for John's OK on a key and cost.
- `python -m scibowl_qb.transcription_review` makes a self-contained review page with each image next to the rendered LaTeX.
- After John's first review: ACCEPT and DO NOT ACCEPT answers are transcribed with LaTeX too, and the parse fails if a printed one is missing. They go in new optional fields `answer.accept_latex` and `answer.do_not_accept_latex`. `schema_version` stays 1 because older readers can ignore optional fields; only changes that break readers bump it.

## 2026-11-23: Never show the answer in a question image or text (QB-28)

- Found while testing the website on v1.0.0: 148 question images reached into the ANSWER row, many showing all or part of the answer, which game mode must never do. The question image now always stops above the ANSWER row (including numerators printed above the word ANSWER).
- Text can't be fixed by position alone: some math fonts report text lower than it is drawn, so question math and answer pieces look the same. Questions with text in the ANSWER row are marked needs_review instead (75 of them), which makes the site show the clean image.

## 2026-11-23: Releases and content checks (QB-09, QB-06)

- The dataset is published as GitHub Releases on this repo, created by pushing a `vX.Y.Z` tag. Each release has `questions.json`, `images.zip` and `manifest.json`. Nothing is published from a pull request.
- The website pins a release version and downloads it at build time, so the site only changes when its pinned version is bumped.
- Content rule: every problem the checks find must be fixed or flagged `needs_review` (images are shown instead). Unflagged problems stop the release.
- Dataset versions: major for a question format change, minor for added or fixed questions, patch for small corrections.

## 2026-11-23: Layout failures (QB-08)

- A numbered line ends a question only if it looks like a question start (a known subject or a printed Short Answer / Multiple Choice). Numbered statements inside a question stay in the question.
- Page footers and separator rows are dropped while reading the PDF, so they never reach question or answer text, and they are left out of the images.
- Questions whose formulas overlap the text in the PDF (mostly set 06 and 07 math) are left flagged `needs_review` with images as the fallback. QB-10 (AI vision) is the fix for those, not more parser rules.

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
