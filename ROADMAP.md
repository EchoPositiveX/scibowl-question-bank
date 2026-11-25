# Roadmap: Science Bowl Question Bank

How this file works:

- Every item has an ID (`QB-NN`) and one line. Add detail in the pull request, not here.
- **Now** is the short-term list: the only items being worked on, one or two at a time. When an item's pull request merges, move it to **Done** with the PR number.
- New ideas go in **Later** or **Parked**. Anyone (person or AI) can add them.
- IDs are never reused, so they stay safe to reference.

## Now

- QB-12 AI-tag questions, a set or two at a time with John's review. First goal: give every question one of the 2022 subjects (biology, chemistry, physics, earth and space, energy, math) in `tags.disciplines`, so older Life, Physical and General Science questions can be studied with the new grouping (website WEB-07)

## Later

- QB-11 Draft a topic list (disciplines and sub-topics) with AI help, for John to edit, then tag sub-topics (QB-12's second step)
- QB-20 Grow the sample file into the golden test set (feeds QB-05) and share it with the website for WEB-01
- QB-03 Cache per-round results so a full run only re-parses PDFs that changed
- QB-33 Publish the printed "(Solution: ...)" working as its own answer field (schema change) instead of only keeping it in answer.raw
- QB-30 Smaller images: 150–200 dpi or palette PNGs would cut images.zip (331 MB) to well under half, which matters for hosting
- QB-25 Find the 6 questions the parser still misses in sets 02–04 (listed in `KNOWN_MISSING` in parse.py)
- QB-13 High school question sets
- QB-14 Local review tool: question image next to rendered text, approve or fix with one click
- QB-15 Accepted alternate answers, for self-check in study mode
- QB-16 Difficulty estimates, first from tags, later from real usage
- QB-17 Detect near-duplicate questions across sets
- QB-18 Pronunciation hints for the moderator

## Parked

(nothing yet)

## Done

- QB-34 Review pages now carry KaTeX 0.16.47 (the website's version) with its script, styles and woff2 fonts inside the HTML, so math renders the same offline and in any viewer
- QB-31 Dropped: after QB-37 no question is flagged needs_review, so there is nothing left for an AI vision API to transcribe
- QB-19 Dropped: covered by `quality.notes` in QB-01
- QB-37 Filled in set 04 Round 4 toss-up 21 (OTEC), whose choices X and Y and answer digit are blank images in the PDF: X) 10, Y) 20, answer Y) 20, via corrections.yaml
- QB-36 Transcribed and John reviewed the 65 questions QB-35 flagged (sets 01, 02, 03, 04, 05, 08 and 13) (#26, #27, #28, #29). Set 13 RR2 toss-up 13's answer is corrected to X) x^10. Published in v1.0.5
- QB-10 Transcribed text and LaTeX for every question the parser flagged needs_review (sets 01 to 09, 11 and 13), from the question images at no API cost, each set reviewed by John before merging (#15 to #17, #21 to #24). Published in v1.0.3; set 04 Round 4 toss-up 21 stayed flagged because its choices are missing from the PDF (filled in by QB-37)
- QB-35 Questions with a fraction or root bar (a short rule with characters just above and below) are flagged needs_review, so the website shows their image: their PDF text comes apart ("convert 1/3 to a decimal" read as "convert rd to a decimal: 3"). 65 more questions flagged; the 61 already transcribed stay verified
- QB-32 Parser fixes from the golden tests: chemical subscripts stay in place (C6H12O6, NH3), a superscript o after a number becomes °, no space before a final ?, printed (Solution: ...) working is dropped from the answer (kept in answer.raw), and ACCEPT lists split on a lower case "or" or on commas between equal numbers. A full parse changes about 700 fields against v1.0.2 and no question's flags
- QB-05 Golden tests: 50 questions from all 16 middle school sets, hand-checked against their images, in `tests/golden/questions.yaml`; `tests/test_golden.py` compares each field. 7 showed parser bugs, fixed in QB-32
- QB-29 Each PDF page is rendered once and all its images are cropped from it: image extraction is about 3x faster, with the same image files (palette PNGs, same size on disk)
- QB-28 Question images stop above the ANSWER row (148 crops in v1.0.0 reached into it, many showing the answer), and 75 questions whose text reaches into that row are marked needs_review so the site shows the image instead
- QB-27 Release workflow can publish from the Run workflow button (version input, main only), so a release no longer needs a tag push
- QB-26 GitHub Actions updated to their Node 24 versions (no more deprecation warning on runs)
- QB-09 Releases: `python -m scibowl_qb.release` builds questions.json, images.zip and manifest.json; pushing a `vX.Y.Z` tag publishes them as a GitHub Release after tests, validation, count and content checks pass; a "Run workflow" trial builds one set with a preview page and publishes nothing
- QB-06 Content checks (`python -m scibowl_qb.checks`): every problem must be fixed or flagged needs_review, or the release stops; found and fixed the 2022 moderator closing script leaking into the last answer
- QB-22 `--jobs N` parses PDFs in parallel (text-only full run under a minute on 4 cores)
- QB-08 needs_review down from 259 to 78: numbered statements ("1) … 2) …") no longer cut a question off before its answer, ANSWER spelling variants are read, blank choice lines (formulas) are kept, and page footers and separator rows are dropped; the old `Bad Questions.txt` cases are fixed
- QB-24 Added set 16 (nine 2022 middle school rounds, 324 questions), supplied by John
- QB-23 Set 15 round 7: replaced the high school PDF that was in the middle school set with the middle school round John supplied (set 15 is now 300 questions)
- QB-07 Every question has a category; "Earth & Space" and split or garbled subject lines fixed; printed Short Answer / Multiple Choice labels after a dash are now read (828 questions became multiple choice with their choices); wrapped choice lines stay with their choice
- QB-21 "Question problem" issue form, docs/fixing-questions.md, and tests/test_reported_issues.py for regression cases
- QB-04 `corrections.yaml`: the 7 overrides moved there with reasons, plus per-question fixes by ID; the parser fails on a correction that matches nothing
- QB-02 (#3) Parser ported: `python -m scibowl_qb.parse` (one set, one round, or all), same 11,374 questions as the old parser, full text-only run in about 2 minutes
- QB-01 (#2) Question format v1: JSON Schema, `python -m scibowl_qb.validate`, docs/question-format.md, 10-question sample file
- QB-00 Repo setup: roadmap, AI instructions, decisions log, Python skeleton, middle school PDFs (#1)
