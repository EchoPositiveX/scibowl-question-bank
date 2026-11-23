# Decisions

Newest first. Each entry: date, decision, and why if it isn't obvious.

## 2026-11-23: Initial plan

- Two repos: `scibowl-question-bank` (this one) and `scibowl-prep-lab` (website). The old `nsb` repo is kept as is, for reference.
- Middle school only for now; high school later.
- DOE question text may be shown publicly on the website.
- First rebuild and improve the pdfplumber parser on a new structure. Only after that, use an AI vision model to produce text with LaTeX, one or two sets at a time with review.
- Topic tagging will be AI-based; the topic list is generated later.
- Images stay as the fallback whenever text isn't verified.
