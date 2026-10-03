import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_email TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'Free',
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  received_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','approved','sent')),
  category TEXT, urgency INTEGER, sentiment TEXT, summary TEXT, draft TEXT,
  ai_source TEXT NOT NULL DEFAULT 'pending',   -- pending | llm | fallback
  ai_error TEXT,
  cost_usd REAL, latency_ms INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with session() as c:
        c.executescript(SCHEMA)
