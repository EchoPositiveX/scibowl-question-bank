"""Science Bowl question bank: parse NSB PDFs into a versioned dataset."""

from pathlib import Path

__version__ = "0.1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
