# Transcriptions (QB-10)

Text and LaTeX for questions the parser can't read reliably, mostly math whose fractions and exponents come apart in the PDF. Each file covers one set: `transcriptions/<level>/<set>.yaml`.

```yaml
source: Who or what made these, and when
questions:
  - id: ms-set01-m-round03-q07-bonus
    question:
      text: "Change the decimal 0.88 to a fraction in lowest terms:"
      latex: "Change the decimal 0.88 to a fraction in lowest terms:"
    answer:
      text: "22/25"
      latex: "$\\frac{22}{25}$"
      accept: ["0.88"]          # optional; replaces the parsed accept list
    choices:                    # only for multiple choice: W, X, Y and Z, each with text and latex
    reviewed: false
```

- `text` is plain text a person can read aloud: `1/3`, `2 1/6`, `x^2`, `√0.5`, `∛5`, `π`, `×`, `−`.
- `latex` is the same with math in `$...$` (KaTeX syntax; chemistry as `\ce{...}`).
- The parser applies these after `corrections.yaml`. An ID that matches no question stops the parse.

## Review

1. Parse the set with images: `python -m scibowl_qb.parse --set set01 -j 4`.
2. Make the review page: `python -m scibowl_qb.transcription_review transcriptions/ms/set01.yaml`. It writes `output/review-ms-set01.html`, with each printed question next to the rendered transcription.
3. For each entry that matches its image exactly, set `reviewed: true`. Fix any that don't.

Until an entry is reviewed, its question stays flagged `needs_review` and the website keeps showing the images. A reviewed entry becomes `text_status: verified`, and the website can show its LaTeX (WEB-05).
