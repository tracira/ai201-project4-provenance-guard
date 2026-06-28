import sqlite3
from datetime import datetime, timezone

DB_PATH = "provenance.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id       TEXT NOT NULL UNIQUE,
                creator_id       TEXT,
                timestamp        TEXT NOT NULL,
                content_preview  TEXT,
                llm_score        REAL,
                stylo_score      REAL,
                final_score      REAL,
                classification   TEXT,
                confidence_level TEXT,
                label_text       TEXT,
                short_text_flag  INTEGER DEFAULT 0,
                status           TEXT NOT NULL DEFAULT 'classified',
                appeal_reasoning TEXT,
                appeal_timestamp TEXT
            )
        """)


def log_submission(record: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO audit_log
                (content_id, creator_id, timestamp, content_preview,
                 llm_score, stylo_score, final_score, classification,
                 confidence_level, label_text, short_text_flag, status)
            VALUES
                (:content_id, :creator_id, :timestamp, :content_preview,
                 :llm_score, :stylo_score, :final_score, :classification,
                 :confidence_level, :label_text, :short_text_flag, :status)
            """,
            record,
        )


def log_appeal(content_id: str, reasoning: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE audit_log
            SET appeal_reasoning = ?, appeal_timestamp = ?, status = 'under_review'
            WHERE content_id = ?
            """,
            (reasoning, datetime.now(timezone.utc).isoformat(), content_id),
        )


def get_entry(content_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM audit_log WHERE content_id = ?", (content_id,)
        ).fetchone()
    return dict(row) if row else None


def read_log(limit: int = 20) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
