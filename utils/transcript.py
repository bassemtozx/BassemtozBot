from datetime import datetime
from pathlib import Path
import discord


async def export_transcript(channel: discord.TextChannel, case_id: str, out_dir: Path | None = None) -> str:
    out_dir = out_dir or Path("transcripts")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{case_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    lines = [f"=== نقل القضية {case_id} ===", f"القناة: {channel.name}", f"التاريخ: {datetime.utcnow().isoformat()}", ""]
    try:
        async for msg in channel.history(limit=500, oldest_first=True):
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M")
            author = msg.author.display_name
            lines.append(f"[{ts}] {author}: {msg.content or '(مرفق/تضمين)'}")
        text = "\n".join(lines)
        path.write_text(text, encoding="utf-8")
        return str(path)
    except Exception:
        return ""
