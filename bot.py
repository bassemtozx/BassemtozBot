import asyncio
import logging
import sys

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID
from database import init_db
from cogs import CasesCog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bot")


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True


async def main():
    init_db()
    bot = commands.Bot(command_prefix="!", intents=intents)
    await bot.add_cog(CasesCog(bot))

    @bot.event
    async def on_ready():
        logger.info("Bot ready: %s", bot.user)
        try:
            gid = (GUILD_ID or "").strip() if GUILD_ID else None
            if gid and str(gid).isdigit():
                guild = discord.Object(id=int(gid))
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
            else:
                await bot.tree.sync()
            logger.info("Slash commands synced")
        except Exception as e:
            logger.exception("Sync failed: %s", e)

    try:
        async with bot:
            await bot.start(DISCORD_TOKEN or None)
    except discord.LoginFailure:
        logger.error("Invalid token")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
