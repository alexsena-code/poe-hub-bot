"""PoE Hub Discord Bot — manages hardware deals, LLM costs, pipelines."""
import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("poe-hub-bot")

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set in .env")


intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log.info("Bot ready as %s (ID: %s)", bot.user, bot.user.id)

    # Load cogs
    for cog in ["cogs.hardware", "cogs.admin", "cogs.context", "alerts.deal_watcher"]:
        try:
            await bot.load_extension(cog)
            log.info("Loaded: %s", cog)
        except Exception as e:
            log.error("Failed to load %s: %s", cog, e)

    # Sync slash commands to guild
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        log.info("Synced %d commands to guild %s", len(synced), GUILD_ID)
    else:
        synced = await bot.tree.sync()
        log.info("Synced %d commands globally", len(synced))


bot.run(TOKEN)
