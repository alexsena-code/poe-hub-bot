"""Admin commands — /status, /costs, /logs."""
import discord
from discord import app_commands
from discord.ext import commands

from services import hardware_api, poehub_api


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="System status overview")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()

        worker = await hardware_api.get_worker_status()
        summary = await hardware_api.get_summary()
        items = await hardware_api.get_items()

        total_deals = sum(s.get("count", 0) for s in summary)

        embed = discord.Embed(title="📊 PoE Hub Status", color=0x5865F2)
        embed.add_field(
            name="Scraper Worker",
            value="🟢 Online" if worker.get("online") else "🔴 Offline",
            inline=True,
        )
        embed.add_field(name="Items Configured", value=str(len(items)), inline=True)
        embed.add_field(name="Total Deals", value=str(total_deals), inline=True)

        if summary:
            lines = []
            for s in summary[:8]:
                lines.append(f"• {s['item_name']}: {s['count']} deals (min R$ {s['min_price']:,.0f})")
            embed.add_field(name="Deals by Item", value="\n".join(lines), inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="costs", description="LLM usage costs")
    @app_commands.describe(days="Number of days to check (default 7)")
    async def costs(self, interaction: discord.Interaction, days: int = 7):
        await interaction.response.defer()

        data = await poehub_api.get_llm_costs(days)

        if not data or "error" in data:
            await interaction.followup.send("Could not fetch LLM costs. API may be down.")
            return

        embed = discord.Embed(title=f"💸 LLM Costs — Last {days} days", color=0xFF6B6B)

        total_cost = data.get("totalCost", 0)
        total_calls = data.get("totalCalls", 0)
        total_input = data.get("totalInputTokens", 0)
        total_output = data.get("totalOutputTokens", 0)

        embed.add_field(name="Total Cost", value=f"${total_cost:.4f}", inline=True)
        embed.add_field(name="API Calls", value=str(total_calls), inline=True)
        embed.add_field(
            name="Tokens",
            value=f"In: {total_input:,} | Out: {total_output:,}",
            inline=False,
        )

        by_model = data.get("byModel", {})
        if by_model:
            lines = [f"• {m}: ${c:.4f}" for m, c in by_model.items()]
            embed.add_field(name="By Model", value="\n".join(lines), inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="logs", description="Recent LLM call logs")
    @app_commands.describe(limit="Number of logs to show (default 5)")
    async def logs(self, interaction: discord.Interaction, limit: int = 5):
        await interaction.response.defer()

        logs = await poehub_api.get_llm_logs(min(limit, 10))

        if not logs:
            await interaction.followup.send("No LLM logs found.")
            return

        embed = discord.Embed(title=f"📝 Recent LLM Logs", color=0xFFA500)

        for log in logs[:limit]:
            model = log.get("model", "?")
            cost = log.get("totalCost", 0)
            latency = log.get("latencyMs", 0)
            prompt = log.get("prompt", "")[:80]

            embed.add_field(
                name=f"{model} — ${cost:.5f} ({latency}ms)",
                value=f"```{prompt}...```",
                inline=False,
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
