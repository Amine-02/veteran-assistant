"""Paths and constants shared by every module."""

from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PACK_DIR = DATA_DIR / "knowledge_pack"
OUT_DIR = ROOT / "outputs"
INGEST_DIR = OUT_DIR / "ingest"  # manifest.csv, chunks.jsonl
RUNS_DIR = OUT_DIR / "runs"  # one folder per eval run + summary.md
LOG_DIR = OUT_DIR / "logs"  # redacted request log, not committed
ANALYSIS_DIR = OUT_DIR / "analysis"  # Section C: traffic mix, cost model

# The brief says to treat this as today.
AS_OF = date(2026, 10, 7)

# Real environment variables win over .env.
load_dotenv(ROOT / ".env")
