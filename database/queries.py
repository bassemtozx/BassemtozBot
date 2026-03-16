from datetime import datetime
from .db import get_db


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def next_case_id(guild_id: int) -> str:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT case_id FROM cases WHERE guild_id = ? ORDER BY id DESC LIMIT 1",
            (guild_id,),
        )
        row = cur.fetchone()
    if not row:
        return "CASE-1001"
    try:
        num = int(row["case_id"].split("-")[-1])
        return f"CASE-{num + 1}"
    except (ValueError, IndexError):
        return "CASE-1001"


def create_case(
    case_id: str,
    guild_id: int,
    channel_id: int,
    creator_id: int,
    defendant_text: str,
    defendant_user_id: int | None,
    case_type: str,
    description: str,
    evidence: str,
    witnesses: str,
) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO cases (
                case_id, guild_id, channel_id, creator_id, defendant_text,
                defendant_user_id, case_type, description, evidence, witnesses,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'مفتوحة', ?)""",
            (
                case_id,
                guild_id,
                channel_id,
                creator_id,
                defendant_text,
                defendant_user_id,
                case_type,
                description,
                evidence,
                witnesses or "",
                _now(),
            ),
        )
        return cur.lastrowid


def get_case_by_id(case_id: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_case_by_channel(channel_id: int) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cases WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_cases(guild_id: int, creator_id: int | None = None, status: str | None = None) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        if creator_id is not None:
            cur.execute(
                "SELECT * FROM cases WHERE guild_id = ? AND creator_id = ? ORDER BY id DESC",
                (guild_id, creator_id),
            )
        elif status:
            cur.execute(
                "SELECT * FROM cases WHERE guild_id = ? AND status = ? ORDER BY id DESC",
                (guild_id, status),
            )
        else:
            cur.execute("SELECT * FROM cases WHERE guild_id = ? ORDER BY id DESC", (guild_id,))
        return [dict(r) for r in cur.fetchall()]


def update_case_status(case_id: str, status: str, closed_at: str | None = None):
    with get_db() as conn:
        cur = conn.cursor()
        if closed_at is not None:
            cur.execute(
                "UPDATE cases SET status = ?, closed_at = ? WHERE case_id = ?",
                (status, closed_at, case_id),
            )
        else:
            cur.execute("UPDATE cases SET status = ? WHERE case_id = ?", (status, case_id))


def assign_staff(case_id: str, staff_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE cases SET assigned_staff_id = ? WHERE case_id = ?", (staff_id, case_id))


def assign_judge(case_id: str, judge_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE cases SET assigned_judge_id = ? WHERE case_id = ?", (judge_id, case_id))


def set_defendant_user(case_id: str, user_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE cases SET defendant_user_id = ? WHERE case_id = ?", (user_id, case_id))


def append_evidence(case_id: str, new_evidence: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT evidence FROM cases WHERE case_id = ?", (case_id,))
        row = cur.fetchone()
        if row:
            prev = row["evidence"] or ""
            cur.execute(
                "UPDATE cases SET evidence = ? WHERE case_id = ?",
                (prev + "\n\n--- إضافة ---\n" + new_evidence, case_id),
            )


def set_verdict(
    case_id: str,
    verdict: str,
    reason: str,
    punishment_duration: str | None,
    appeal_allowed: bool,
):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE cases SET final_verdict = ?, verdict_reason = ?,
               punishment_duration = ?, appeal_allowed = ?, status = 'صدر الحكم'
               WHERE case_id = ?""",
            (verdict, reason, punishment_duration or "", 1 if appeal_allowed else 0, case_id),
        )


def lock_verdict(case_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE cases SET verdict_locked = 1 WHERE case_id = ?", (case_id,))


def unlock_verdict(case_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE cases SET verdict_locked = 0 WHERE case_id = ?", (case_id,))


def add_note(case_id: str, author_id: int, note: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO case_notes (case_id, author_id, note, created_at) VALUES (?, ?, ?, ?)",
            (case_id, author_id, note, _now()),
        )


def get_notes(case_id: str) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM case_notes WHERE case_id = ? ORDER BY id", (case_id,))
        return [dict(r) for r in cur.fetchall()]


def log_action(case_id: str, actor_id: int, action: str, details: str | None = None):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO case_logs (case_id, actor_id, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (case_id, actor_id, action, details or "", _now()),
        )


def get_logs(case_id: str) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM case_logs WHERE case_id = ? ORDER BY id", (case_id,))
        return [dict(r) for r in cur.fetchall()]


def submit_appeal(case_id: str, user_id: int, reason: str, new_evidence: str, details: str) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO case_appeals (case_id, submitted_by, reason, new_evidence, details, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'معلق', ?)""",
            (case_id, user_id, reason, new_evidence, details, _now()),
        )
        return cur.lastrowid


def get_pending_appeal(case_id: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM case_appeals WHERE case_id = ? AND status = 'معلق' ORDER BY id DESC LIMIT 1",
            (case_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def set_appeal_status(appeal_id: int, status: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE case_appeals SET status = ? WHERE id = ?", (status, appeal_id))


def get_appeals(case_id: str) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM case_appeals WHERE case_id = ? ORDER BY id", (case_id,))
        return [dict(r) for r in cur.fetchall()]


def update_channel_id(case_id: str, channel_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE cases SET channel_id = ? WHERE case_id = ?", (channel_id, case_id))
