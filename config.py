import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = os.getenv("GUILD_ID")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0") or "0")
JUDGE_ROLE_ID = int(os.getenv("JUDGE_ROLE_ID", "0") or "0")
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0") or "0")
OPEN_CASES_CATEGORY_ID = int(os.getenv("OPEN_CASES_CATEGORY_ID", "0") or "0")
CLOSED_CASES_CATEGORY_ID = int(os.getenv("CLOSED_CASES_CATEGORY_ID", "0") or "0")
VERDICTS_CHANNEL_ID = int(os.getenv("VERDICTS_CHANNEL_ID", "0") or "0")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or "0")

DB_PATH = os.getenv("DB_PATH", "cases.db")

CASE_STATUSES = [
    "مفتوحة",
    "قيد المراجعة",
    "بانتظار رد المتهم",
    "بانتظار أدلة إضافية",
    "تحت المداولة",
    "صدر الحكم",
    "مغلقة",
    "مؤرشفة",
]

APPEAL_STATUSES = ["معلق", "مقبول", "مرفوض"]
