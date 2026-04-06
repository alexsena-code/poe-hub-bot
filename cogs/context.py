"""Context ingestion — /save, /queue, /approve."""
import discord
from discord import app_commands
from discord.ext import commands

from services import poehub_api


class Context(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In-memory queue for now (will move to DB later)
        self._queue: list[dict] = []
        self._next_id = 1

    @app_commands.command(name="save", description="Save a URL/link for later processing")
    @app_commands.describe(
        url="URL to save",
        notes="Optional notes about this content",
        category="Content category",
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="Guide", value="guide"),
        app_commands.Choice(name="Build", value="build"),
        app_commands.Choice(name="News", value="news"),
        app_commands.Choice(name="Reference", value="reference"),
        app_commands.Choice(name="Other", value="other"),
    ])
    async def save(
        self,
        interaction: discord.Interaction,
        url: str,
        notes: str | None = None,
        category: str = "other",
    ):
        item = {
            "id": self._next_id,
            "url": url,
            "notes": notes or "",
            "category": category,
            "saved_by": interaction.user.display_name,
            "status": "pending",
        }
        self._queue.append(item)
        self._next_id += 1

        embed = discord.Embed(
            title="📌 Saved for Review",
            color=0x00D4AA,
            description=f"**URL:** {url}\n**Category:** {category}\n**Notes:** {notes or 'none'}",
        )
        embed.set_footer(text=f"ID: {item['id']} • Saved by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="queue", description="List pending items for review")
    async def queue(self, interaction: discord.Interaction):
        pending = [i for i in self._queue if i["status"] == "pending"]

        if not pending:
            await interaction.response.send_message("Queue is empty! 🎉")
            return

        embed = discord.Embed(title="📋 Pending Review Queue", color=0xFFA500)

        for item in pending[:20]:
            embed.add_field(
                name=f"#{item['id']} — {item['category']}",
                value=f"[Link]({item['url']})\n{item['notes'][:50] if item['notes'] else 'No notes'}\n└ by {item['saved_by']}",
                inline=False,
            )

        embed.set_footer(text=f"{len(pending)} pending items")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="approve", description="Approve a queued item for ingestion")
    @app_commands.describe(item_id="ID of the item to approve")
    async def approve(self, interaction: discord.Interaction, item_id: int):
        item = next((i for i in self._queue if i["id"] == item_id), None)

        if not item:
            await interaction.response.send_message(f"Item #{item_id} not found")
            return

        if item["status"] != "pending":
            await interaction.response.send_message(f"Item #{item_id} is already {item['status']}")
            return

        item["status"] = "approved"
        # TODO: trigger Qdrant ingestion here

        embed = discord.Embed(
            title=f"✅ Approved #{item_id}",
            color=0x00FF88,
            description=f"**URL:** {item['url']}\n**Category:** {item['category']}",
        )
        embed.set_footer(text="Queued for Qdrant ingestion")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Context(bot))
