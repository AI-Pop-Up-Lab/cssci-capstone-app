from __future__ import annotations

import json
from datetime import datetime

from app.db.conn import get_persona_conn, get_chat_conn


# ============================================================
# SCHEMA: PERSONA DB (static / truth source)
# ============================================================

PERSONA_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS personas (
  persona_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  profile_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (persona_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS question_bank (
  question_id TEXT PRIMARY KEY,
  question_text TEXT NOT NULL,
  answer_type TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  sensitive_flags_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS survey_answers (
  persona_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  answer_value TEXT,
  answer_text TEXT NOT NULL,
  wave TEXT NOT NULL,
  confidence REAL,
  source TEXT NOT NULL,
  calibration_tag TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (persona_id, snapshot_id, question_id, wave),
  FOREIGN KEY (question_id) REFERENCES question_bank(question_id)
);

CREATE INDEX IF NOT EXISTS idx_answers_persona ON survey_answers(persona_id, snapshot_id);
"""


# ============================================================
# SCHEMA: CHAT DB (runtime / history)
# ============================================================

CHAT_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  model_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
  message_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL, -- user | assistant
  content TEXT NOT NULL,
  citations_json TEXT,
  trace_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
"""


# ============================================================
# INIT
# ============================================================

def init_persona_db() -> None:
    with get_persona_conn() as conn:
        conn.executescript(PERSONA_SCHEMA_SQL)
        conn.commit()


def init_chat_db() -> None:
    with get_chat_conn() as conn:
        conn.executescript(CHAT_SCHEMA_SQL)
        conn.commit()


def init_db() -> None:
    """
    Convenience initializer used by app startup.
    Creates both databases with their respective schemas.
    """
    init_persona_db()
    init_chat_db()


# ============================================================
# SEED (PERSONA DB ONLY)
# ============================================================

def seed_demo_data() -> None:
    """
    Seed minimal demo persona data IF persona DB is empty.

    IMPORTANT:
    - This seeds ONLY persona.db (personas/question_bank/survey_answers).
    - It does NOT seed chat history.
    """
    with get_persona_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM personas").fetchone()
        if row and row["c"] > 0:
            return

        now = datetime.utcnow().isoformat()

        personas = [
            (
                "P_0001",
                "2026_wave_1",
                json.dumps(
                    {
                        "display_name": "Persona X",
                        "age_band": "25-34",
                        "region_bucket": "NL",
                        "gender": "female",
                        "education_level": "Bachelor",
                        "interest_clusters": ["climate", "tech", "health"],
                        "disclosure": "Synthetic persona generated from public statistics.",
                    },
                    ensure_ascii=False,
                ),
                now,
            ),
            (
                "P_0002",
                "2026_wave_1",
                json.dumps(
                    {
                        "display_name": "Persona Y",
                        "age_band": "35-44",
                        "region_bucket": "NL",
                        "gender": "male",
                        "education_level": "Master",
                        "interest_clusters": ["economy", "public policy", "sports"],
                        "disclosure": "Synthetic persona generated from public statistics.",
                    },
                    ensure_ascii=False,
                ),
                now,
            ),
        ]
        conn.executemany(
            "INSERT INTO personas(persona_id, snapshot_id, profile_json, created_at) VALUES (?, ?, ?, ?)",
            personas,
        )

        questions = [
            ("Q1", "Do you support a carbon tax?", "single", json.dumps(["climate", "tax"]), json.dumps([])),
            ("Q2", "Should the government increase defense spending?", "single", json.dumps(["security"]), json.dumps([])),
            ("Q3", "How concerned are you about inflation?", "scale", json.dumps(["economy"]), json.dumps([])),
            ("Q4", "What is your top policy priority?", "text", json.dumps(["policy"]), json.dumps([])),
        ]
        conn.executemany(
            "INSERT INTO question_bank(question_id, question_text, answer_type, tags_json, sensitive_flags_json) VALUES (?, ?, ?, ?, ?)",
            questions,
        )

        answers = [
            ("P_0001", "2026_wave_1", "Q1", "Yes", "Yes, I support a carbon tax.", "2026_wave_1", 0.72, "generated_from_stats_v1", "calib_a", now),
            ("P_0001", "2026_wave_1", "Q2", "No", "No, I would not increase defense spending.", "2026_wave_1", 0.61, "generated_from_stats_v1", "calib_a", now),
            ("P_0001", "2026_wave_1", "Q4", None, "Climate policy is my top priority.", "2026_wave_1", 0.58, "generated_from_stats_v1", "calib_a", now),

            ("P_0002", "2026_wave_1", "Q1", "No", "No, I do not support a carbon tax.", "2026_wave_1", 0.66, "generated_from_stats_v1", "calib_a", now),
            ("P_0002", "2026_wave_1", "Q3", "High", "I am highly concerned about inflation.", "2026_wave_1", 0.70, "generated_from_stats_v1", "calib_a", now),
            ("P_0002", "2026_wave_1", "Q4", None, "Lowering living costs is my top priority.", "2026_wave_1", 0.55, "generated_from_stats_v1", "calib_a", now),
        ]
        conn.executemany(
            """INSERT INTO survey_answers(
                   persona_id, snapshot_id, question_id, answer_value, answer_text, wave,
                   confidence, source, calibration_tag, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            answers,
        )

        conn.commit()
