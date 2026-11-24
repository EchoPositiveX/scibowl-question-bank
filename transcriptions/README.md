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
      accept:                   # every (ACCEPT: ...) printed in the answer, each with text and latex
        - text: "0.88"
          latex: "$0.88$"
      do_not_accept:            # the same for (DO NOT ACCEPT: ...)
    choices:                    # only for multiple choice: W, X, Y and Z, each with text and latex
    reviewed: false
```

- `text` is plain text a person can read aloud: `1/3`, `2 1/6`, `x^2`, `√0.5`, `∛5`, `π`, `×`, `−`.
- `latex` is the same with math in `$...$` (KaTeX syntax; chemistry as `\ce{...}`).
- The parser applies these after `corrections.yaml`. An ID that matches no question stops the parse.
- Everything printed in the answer is transcribed, not only the main answer. If the printed answer has ACCEPT or DO NOT ACCEPT and the entry doesn't, the parse stops with a message that says so. They come out in the data as `answer.accept` and `answer.accept_latex` (and `do_not_accept`, `do_not_accept_latex`), in the same order.

## Checklist for each entry

1. The question, with every number, variable, exponent and root from the image.
2. The main answer.
3. Each ACCEPT and DO NOT ACCEPT, with LaTeX like the main answer.
4. Anything in brackets after the answer (a pronunciation) is left out: the parser keeps it from the PDF.

## Review

1. Parse the set with images: `python -m scibowl_qb.parse --set set01 -j 4`.
2. Make the review page: `python -m scibowl_qb.transcription_review transcriptions/ms/set01.yaml`. It writes `output/review-ms-set01.html`, with each printed question next to the rendered transcription. Add `--todo` to show only the entries not reviewed yet.
3. John checks the rendered version against the image and says which are right. Those get `reviewed: true`; the rest are fixed and reviewed again.

Until an entry is reviewed, its question stays flagged `needs_review` and the website keeps showing the images. A reviewed entry becomes `text_status: verified`, and the website can show its LaTeX (WEB-05).
