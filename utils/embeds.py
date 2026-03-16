import discord
from datetime import datetime


def _truncate(s: str, max_len: int = 1024) -> str:
    if not s:
        return "—"
    s = str(s).strip()
    return (s[: max_len - 3] + "...") if len(s) > max_len else s


def build_case_embed(case: dict, guild: discord.Guild) -> discord.Embed:
    creator = guild.get_member(case["creator_id"])
    staff = guild.get_member(case["assigned_staff_id"]) if case["assigned_staff_id"] else None
    judge = guild.get_member(case["assigned_judge_id"]) if case["assigned_judge_id"] else None
    creator_name = creator.display_name if creator else str(case["creator_id"])
    staff_name = staff.display_name if staff else ("—" if not case["assigned_staff_id"] else str(case["assigned_staff_id"]))
    judge_name = judge.display_name if judge else ("—" if not case["assigned_judge_id"] else str(case["assigned_judge_id"]))

    emb = discord.Embed(
        title=f"📋 القضية {case['case_id']}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    emb.add_field(name="رقم القضية", value=case["case_id"], inline=True)
    emb.add_field(name="الحالة", value=case["status"], inline=True)
    emb.add_field(name="مقدم الشكوى", value=creator_name, inline=True)
    emb.add_field(name="المشتكى عليه", value=_truncate(case["defendant_text"], 256), inline=True)
    emb.add_field(name="نوع القضية", value=_truncate(case["case_type"], 256), inline=True)
    emb.add_field(name="الوصف", value=_truncate(case["description"], 1024), inline=False)
    emb.add_field(name="الأدلة", value=_truncate(case["evidence"], 1024), inline=False)
    emb.add_field(name="الشهود", value=_truncate(case["witnesses"] or "—", 512), inline=False)
    emb.add_field(name="المشرف المسؤول", value=staff_name, inline=True)
    emb.add_field(name="القاضي المسؤول", value=judge_name, inline=True)
    emb.add_field(name="الحكم النهائي", value=_truncate(case["final_verdict"] or "—", 512), inline=False)
    if case.get("verdict_reason"):
        emb.add_field(name="سبب الحكم", value=_truncate(case["verdict_reason"], 512), inline=False)
    if case.get("punishment_duration"):
        emb.add_field(name="مدة العقوبة", value=_truncate(case["punishment_duration"], 256), inline=True)
    emb.add_field(name="تاريخ الإنشاء", value=case["created_at"], inline=True)
    if case.get("closed_at"):
        emb.add_field(name="تاريخ الإغلاق", value=case["closed_at"], inline=True)
    emb.set_footer(text="نظام إدارة المحاضر")
    return emb


def build_verdict_announce_embed(case: dict, guild: discord.Guild) -> discord.Embed:
    creator = guild.get_member(case["creator_id"])
    creator_name = creator.display_name if creator else str(case["creator_id"])
    emb = discord.Embed(
        title=f"⚖️ صدر الحكم — {case['case_id']}",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow(),
    )
    emb.add_field(name="رقم القضية", value=case["case_id"], inline=True)
    emb.add_field(name="مقدم الشكوى", value=creator_name, inline=True)
    emb.add_field(name="المشتكى عليه", value=_truncate(case["defendant_text"], 256), inline=True)
    emb.add_field(name="نوع الحكم", value=_truncate(case["final_verdict"], 512), inline=False)
    emb.add_field(name="سبب الحكم", value=_truncate(case.get("verdict_reason") or "—", 1024), inline=False)
    if case.get("punishment_duration"):
        emb.add_field(name="مدة العقوبة", value=_truncate(case["punishment_duration"], 256), inline=True)
    emb.add_field(name="الاستئناف", value="متاح" if case.get("appeal_allowed") else "غير متاح", inline=True)
    emb.set_footer(text="نظام إدارة المحاضر")
    return emb


def build_log_embed(logs: list, case_id: str, guild: discord.Guild) -> discord.Embed:
    emb = discord.Embed(
        title=f"سجل القضية {case_id}",
        color=discord.Color.dark_gray(),
        timestamp=datetime.utcnow(),
    )
    lines = []
    for log in logs[-25:]:
        actor = guild.get_member(log["actor_id"])
        name = actor.display_name if actor else str(log["actor_id"])
        detail = f" — {log['details']}" if log.get("details") else ""
        lines.append(f"**{log['created_at']}** | {name}: {log['action']}{detail}")
    emb.description = "\n".join(lines) if lines else "لا توجد سجلات."
    emb.set_footer(text="نظام إدارة المحاضر")
    return emb


def build_list_embed(cases: list, title: str) -> discord.Embed:
    emb = discord.Embed(title=title, color=discord.Color.blue(), timestamp=datetime.utcnow())
    if not cases:
        emb.description = "لا توجد قضايا."
        return emb
    lines = []
    for c in cases[:20]:
        lines.append(f"• **{c['case_id']}** — {c['status']} — {c['case_type'][:30]}")
    emb.description = "\n".join(lines)
    emb.set_footer(text="نظام إدارة المحاضر")
    return emb
