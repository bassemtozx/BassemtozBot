import discord
from config import LOG_CHANNEL_ID
from .embeds import build_log_embed
from database.queries import get_logs


async def send_log_embed(bot: discord.Client, case_id: str, action: str, actor: discord.Member, details: str | None = None):
    if not LOG_CHANNEL_ID:
        return
    ch = bot.get_channel(LOG_CHANNEL_ID)
    if not ch or not isinstance(ch, discord.TextChannel):
        return
    try:
        logs = get_logs(case_id)
        emb = build_log_embed(logs, case_id, ch.guild)
        emb.title = f"📌 {action} — {case_id}"
        if details:
            emb.add_field(name="التفاصيل", value=details[:1024], inline=False)
        await ch.send(embed=emb)
    except Exception:
        pass
