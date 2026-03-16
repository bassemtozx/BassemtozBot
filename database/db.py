import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import DB_PATH


def _db_path():
    p = Path(DB_PATH)
    if not p.is_absolute():
        p = Path(__file__).parent.parent / p
    return str(p)


@contextmanager
def get_db():
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER,
                creator_id INTEGER NOT NULL,
                defendant_text TEXT NOT NULL,
                defendant_user_id INTEGER,
                case_type TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT NOT NULL,
                witnesses TEXT,
                status TEXT NOT NULL DEFAULT 'مفتوحة',
                assigned_staff_id INTEGER,
                assigned_judge_id INTEGER,
                final_verdict TEXT,
                verdict_reason TEXT,
                punishment_duration TEXT,
                appeal_allowed INTEGER DEFAULT 0,
                verdict_locked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                closed_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS case_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                actor_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS case_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS case_appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                submitted_by INTEGER NOT NULL,
                reason TEXT NOT NULL,
                new_evidence TEXT,
                details TEXT,
                status TEXT NOT NULL DEFAULT 'معلق',
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_guild ON cases(guild_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_creator ON cases(creator_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_case_logs_case ON case_logs(case_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_case_notes_case ON case_notes(case_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_case_appeals_case ON case_appeals(case_id)")
