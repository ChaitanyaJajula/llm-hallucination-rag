import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("TRIAGE_MODEL", "claude-haiku-4-5-20251001")
DB_PATH = os.environ.get("TRIAGE_DB", str(ROOT / "triage.db"))
SAMPLE_CSV = ROOT / "data" / "sample_tickets.csv"

LLM_TIMEOUT_S = float(os.environ.get("TRIAGE_LLM_TIMEOUT", "20"))
LLM_ATTEMPTS = int(os.environ.get("TRIAGE_LLM_ATTEMPTS", "2"))

# USD per million tokens (input, output). Used only for the per-ticket cost estimate.
PRICES = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5-5": (3.0, 15.0),
}
