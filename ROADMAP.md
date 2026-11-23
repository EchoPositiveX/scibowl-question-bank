# Roadmap: Science Bowl Question Bank

How this file works:

- Every item has an ID (`QB-NN`) and one line. Add detail in the pull request, not here.
- Work happens from **Now**, one or two items at a time. When an item's pull request merges, move it to **Done** with the PR number.
- New ideas go in **Nice to have** or **Parked**. Anyone (person or AI) can add them.
- IDs are never reused, so they stay safe to reference.

## Now

- QB-01 Question format: JSON Schema for one question, a validator script, and a short doc of each field
- QB-02 Port the parser from the old `nsb` repo onto the new format, with a command line that can run one set, one round, or everything

## Next

- QB-03 Cache per-round results so a full run only re-parses PDFs that changed
- QB-04 Corrections file (`corrections.yaml`) to replace the 7 hard-coded overrides, each with a reason
- QB-05 Golden tests: about 50 hand-checked questions across sets, compared field by field
- QB-06 Content checks across all questions: answer present, multiple choice has W–Z, valid category, no footer text
- QB-07 Normalize subjects to the official NSB categories, keeping the raw label
- QB-08 Fix known layout failures: questions across a page break, footers in answers, the cases in the old `Bad Questions.txt`
- QB-09 Publish versioned releases (questions JSON + images) for the website to download
- QB-10 AI vision step to produce text with LaTeX/mhchem, prototyped on 1–2 sets and reviewed before continuing
- QB-11 Draft a topic list (disciplines and sub-topics) with AI help, for John to edit
- QB-12 AI-tag questions against the topic list, a set or two at a time

## Nice to have

- QB-13 High school question sets
- QB-14 Local review tool: question image next to rendered text, approve or fix with one click
- QB-15 Accepted alternate answers, for self-check in study mode
- QB-16 Difficulty estimates, first from tags, later from real usage
- QB-17 Detect near-duplicate questions across sets
- QB-18 Pronunciation hints for the moderator
- QB-19 Track parse notes per question: what was corrected and why

## Parked

(nothing yet)

## Done

- QB-00 Repo setup: roadmap, AI instructions, decisions log, Python skeleton, middle school PDFs
