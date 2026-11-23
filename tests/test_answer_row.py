"""Question text and images must never show the answer (QB-28).

Some PDFs set a fraction's numerator, or the answer value, a little above the word
ANSWER, and some math fonts report text positions lower than they are drawn. Either
way, text can reach into the ANSWER row. Such questions are marked needs_review (the
site then shows the image), and the question image always stops above the ANSWER row.
"""

from functools import lru_cache

from PIL import Image

from scibowl_qb import RAW_DIR
from scibowl_qb.convert import to_question
from scibowl_qb.extract import extract_round


@lru_cache(maxsize=None)
def _round(pdf_rel: str) -> dict:
    return {q["id"]: q for q in (to_question(rq) for rq in extract_round(RAW_DIR / pdf_rel, RAW_DIR))}


def test_answer_numerator_in_question_is_marked():
    # Change 0.88 to a fraction: the answer's numerator "22" sits above the ANSWER line.
    q = _round("ms/set01/m_round03.pdf")["ms-set01-m-round03-q07-bonus"]
    assert "needs_review" in q["quality"]["flags"]
    assert any("ANSWER row" in n for n in q["quality"]["notes"])


def test_plain_questions_are_not_marked():
    q = _round("ms/set01/m_round03.pdf")["ms-set01-m-round03-q01-tossup"]
    assert "needs_review" not in q["quality"]["flags"]


def test_question_image_stops_above_answer(tmp_path):
    raw = extract_round(RAW_DIR / "ms/set06/Round8.pdf", RAW_DIR, images_dir=tmp_path)
    rq = next(r for r in raw if r.number == 12 and r.part == "tossup")
    question = Image.open(tmp_path / rq.images["question"].removeprefix("images/"))
    entire = Image.open(tmp_path / rq.images["entire"].removeprefix("images/"))
    # The whole-question image includes the answer row; the question image must be clearly shorter.
    assert question.height < entire.height * 0.75
