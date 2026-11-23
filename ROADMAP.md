# Roadmap: Science Bowl Question Bank

How this file works:

- Every item has an ID (`QB-NN`) and one line. Add detail in the pull request, not here.
- Work happens from **Now**, one or two items at a time. When an item's pull request merges, move it to **Done** with the PR number.
- New ideas go in **Nice to have** or **Parked**. Anyone (person or AI) can add them.
- IDs are never reused, so they stay safe to reference.

## Now

- QB-08 Fix known layout failures: 247 questions with no answer found (cause not yet investigated), 46 multiple choice questions missing choices or answer letter, footers in answers, the cases in the old `Bad Questions.txt`

## Next

- QB-20 Grow the sample file into the golden test set (feeds QB-05) and share it with the website for WEB-01
- QB-03 Cache per-round results so a full run only re-parses PDFs that changed
- QB-05 Golden tests: about 50 hand-checked questions across sets, compared field by field
- QB-06 Content checks across all questions: answer present, multiple choice has W–Z, valid category, no footer text
- QB-09 Publish versioned releases (questions JSON + images) for the website to download
- QB-10 AI vision step to produce text with LaTeX/mhchem, prototyped on 1–2 sets and reviewed before continuing
- QB-11 Draft a topic list (disciplines and sub-topics) with AI help, for John to edit
- QB-12 AI-tag questions against the topic list, a set or two at a time

## Nice to have

- QB-22 Parse in parallel to cut the full run with images (about 70 minutes single-threaded)
- QB-13 High school question sets
- QB-14 Local review tool: question image next to rendered text, approve or fix with one click
- QB-15 Accepted alternate answers, for self-check in study mode
- QB-16 Difficulty estimates, first from tags, later from real usage
- QB-17 Detect near-duplicate questions across sets
- QB-18 Pronunciation hints for the moderator
- QB-23 Decide what to do with `set15/Set-7-HS-2021`, a high school round inside the middle school sets (it uses Biology, Chemistry and Physics)
- QB-19 ~~Track parse notes per question~~ (covered by `quality.notes` in QB-01)

## Parked

(nothing yet)

## Done

- QB-07 Every question has a category; "Earth & Space" and split or garbled subject lines fixed; printed Short Answer / Multiple Choice labels after a dash are now read (828 questions became multiple choice with their choices); wrapped choice lines stay with their choice
- QB-21 "Question problem" issue form, docs/fixing-questions.md, and tests/test_reported_issues.py for regression cases
- QB-04 `corrections.yaml`: the 7 overrides moved there with reasons, plus per-question fixes by ID; the parser fails on a correction that matches nothing
- QB-02 (#3) Parser ported: `python -m scibowl_qb.parse` (one set, one round, or all), same 11,374 questions as the old parser, full text-only run in about 2 minutes
- QB-01 (#2) Question format v1: JSON Schema, `python -m scibowl_qb.validate`, docs/question-format.md, 10-question sample file
- QB-00 Repo setup: roadmap, AI instructions, decisions log, Python skeleton, middle school PDFs (#1)
