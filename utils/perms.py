import discord
from config import STAFF_ROLE_ID, JUDGE_ROLE_ID, ADMIN_ROLE_ID


def is_staff(member: discord.Member) -> bool:
    if not member or not member.guild:
        return False
    if ADMIN_ROLE_ID and any(r.id == ADMIN_ROLE_ID for r in member.roles):
        return True
    if JUDGE_ROLE_ID and any(r.id == JUDGE_ROLE_ID for r in member.roles):
        return True
    if STAFF_ROLE_ID and any(r.id == STAFF_ROLE_ID for r in member.roles):
        return True
    return member.guild_permissions.administrator


def is_judge(member: discord.Member) -> bool:
    if not member or not member.guild:
        return False
    if ADMIN_ROLE_ID and any(r.id == ADMIN_ROLE_ID for r in member.roles):
        return True
    if JUDGE_ROLE_ID and any(r.id == JUDGE_ROLE_ID for r in member.roles):
        return True
    return member.guild_permissions.administrator


def is_admin(member: discord.Member) -> bool:
    if not member or not member.guild:
        return False
    if ADMIN_ROLE_ID and any(r.id == ADMIN_ROLE_ID for r in member.roles):
        return True
    return member.guild_permissions.administrator


def can_manage_case(member: discord.Member) -> bool:
    return is_staff(member)


def can_issue_verdict(member: discord.Member) -> bool:
    return is_judge(member)


def can_override_verdict(member: discord.Member) -> bool:
    return is_admin(member)
