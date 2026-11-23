"""Sanity checks on the raw PDFs, so later parser tests have a known starting point."""

from collections import Counter

from scibowl_qb import RAW_DIR

EXPECTED_MS_PDFS_PER_SET = {
    "set01": 18, "set02": 10, "set03": 15, "set04": 17, "set05": 16,
    "set06": 17, "set07": 15, "set08": 17, "set09": 17, "set10": 17,
    "set11": 17, "set12": 17, "set13": 21, "set14": 17, "set15": 10,
}


def ms_pdfs():
    return sorted((RAW_DIR / "ms").glob("set*/*.pdf"))


def test_ms_pdf_counts_per_set():
    counts = Counter(p.parent.name for p in ms_pdfs())
    assert dict(counts) == EXPECTED_MS_PDFS_PER_SET


def test_ms_pdfs_are_pdfs():
    not_pdf = [p.name for p in ms_pdfs() if p.read_bytes()[:5] != b"%PDF-"]
    assert not_pdf == []
