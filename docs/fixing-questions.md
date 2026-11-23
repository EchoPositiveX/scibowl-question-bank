# Fixing reported question problems

Anyone can report a problem with the **Question problem** issue form (Issues > New issue). Later, flags from the website's review page (WEB-22) will arrive here as issues too.

## The workflow

1. **Triage.** Find the question in `output/questions.json` (or parse just its round) and compare it with the PDF and the question image. Label the issue:
   - `question-problem`: confirmed, needs a fix
   - `not-a-problem`: the question is right; close with a short explanation
   - `source-error`: the PDF itself is wrong; fix with a correction and say so in the reason
2. **Decide: one-off or pattern?**
   - **One-off** (a typo, one wrong answer, one garbled formula): add an entry under `questions:` in `corrections.yaml`, matched by ID, with a plain-words reason.
   - **Wrong number, part or subject that changes the ID**: add an entry under `extract:` instead.
   - **Pattern** (the same kind of failure in several places, e.g. footers in answers): fix the parser. Check the whole-run counts before and after, so the fix doesn't break other rounds.
3. **Add a regression test.** Add a case to `REPORTED` in `tests/test_reported_issues.py` with the issue number, the question ID, and the field values that should now be right. This keeps the fix from quietly coming undone.
4. **Open a pull request** that says `Fixes #<issue>` so the issue closes when John merges it. Several small reports can go in one PR.

## Batch fixing with AI

To work through reports in bulk, ask Claude to "work through the open question-problem issues". It should:

- read each open issue, check it against the PDF and image,
- propose the fix (correction or parser change) plus a regression test,
- open one PR for a small batch, listing what it did for each issue and any it couldn't confirm,
- never close an issue without a merged fix or a stated reason.

## What counts as fixed

- The question passes `python -m scibowl_qb.validate`.
- The regression test passes.
- If the text now matches the image exactly, set `quality.text_status: verified` in the correction.
