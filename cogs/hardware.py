"""Hardware deals commands — /deals, /price, /scrape, /alert."""
import discord
from discord import app_commands
from discord.ext import commands

from services import hardware_api


def _format_price(price: float) -> str:
    return f"R$ {price:,.0f}".replace(",", ".")


class Hardware(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="deals", description="List best deals for an item")
    @app_commands.describe(item="Item name (e.g. GTX 1080 Ti)")
    async def deals(self, interaction: discord.Interaction, item: str | None = None):
        await interaction.response.defer()

        deals = await hardware_api.get_deals(item_name=item, limit=15)
        if not deals:
            await interaction.followup.send("No deals found." + (f" (filter: {item})" if item else ""))
            return

        embed = discord.Embed(
            title=f"🔍 Deals" + (f" — {item}" if item else ""),
            color=0x00FF88,
        )

        lines = []
        for d in deals[:15]:
            price = _format_price(d["price"])
            title = d["title"][:45]
            loc = d.get("location", "")[:20]
            url = d.get("url", "")
            lines.append(f"**{price}** — [{title}]({url})\n└ {d['item_name']} • {loc}")

        embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"{len(deals)} deals shown")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="price", description="Price check for an item")
    @app_commands.describe(item="Item name (e.g. GTX 1080 Ti)")
    async def price(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()

        summary = await hardware_api.get_summary()
        matches = [s for s in summary if item.lower() in s["item_name"].lower()]

        if not matches:
            await interaction.followup.send(f"No price data for '{item}'")
            return

        embed = discord.Embed(title=f"💰 Price Check", color=0xFFD700)

        for s in matches:
            embed.add_field(
                name=s["item_name"],
                value=(
                    f"**Min:** {_format_price(s['min_price'])}\n"
                    f"**Avg:** {_format_price(s['avg_price'])}\n"
                    f"**Max:** {_format_price(s['max_price'])}\n"
                    f"Deals: {s['count']} ({s['source'].upper()})"
                ),
                inline=True,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="scrape", description="Trigger a scrape cycle")
    @app_commands.describe(item="Item name to scrape (leave empty for all)")
    async def scrape(self, interaction: discord.Interaction, item: str | None = None):
        await interaction.response.defer()

        # Find item ID if name provided
        item_id = None
        if item:
            items = await hardware_api.get_items()
            match = next((i for i in items if item.lower() in i["name"].lower()), None)
            if match:
                item_id = match["id"]
            else:
                await interaction.followup.send(f"Item '{item}' not found")
                return

        worker = await hardware_api.get_worker_status()
        if not worker.get("online"):
            await interaction.followup.send("⚠️ Scraper worker is offline. Start it on your PC.")
            return

        result = await hardware_api.trigger_scrape(item_id)
        status = result.get("status", "error")

        if status == "dispatched":
            count = result.get("items", 0)
            await interaction.followup.send(
                f"🚀 Scrape dispatched! {count} item(s) queued. Worker is processing..."
            )
        else:
            await interaction.followup.send(f"Scrape result: {status}")

    @app_commands.command(name="items", description="List configured search items")
    async def items_list(self, interaction: discord.Interaction):
        await interaction.response.defer()

        items = await hardware_api.get_items()
        if not items:
            await interaction.followup.send("No items configured")
            return

        embed = discord.Embed(title="📋 Search Items", color=0x5865F2)

        for cat in ["gpu", "cpu-kit", "ram", "psu", "ssd", "motherboard"]:
            cat_items = [i for i in items if i["category"] == cat]
            if cat_items:
                lines = [f"• {i['name']} (max {_format_price(i['max_price'])})" for i in cat_items]
                embed.add_field(name=cat.upper(), value="\n".join(lines), inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="vm", description="Quick VM calculation")
    @app_commands.describe(
        vram="Total VRAM (GB)",
        ram="Total RAM (GB)",
        threads="Total CPU threads",
        vm_vram="VRAM per VM (default 0.6)",
        vm_ram="RAM per VM (default 4)",
        vm_threads="Threads per VM (default 2)",
    )
    async def vm_calc(
        self,
        interaction: discord.Interaction,
        vram: float,
        ram: int,
        threads: int,
        vm_vram: float = 0.6,
        vm_ram: int = 4,
        vm_threads: int = 2,
    ):
        host_ram = 4
        host_threads = 2

        avail_vram = vram
        avail_ram = max(0, ram - host_ram)
        avail_threads = max(0, threads - host_threads)

        max_by_vram = int(avail_vram / vm_vram) if vm_vram > 0 else 999
        max_by_ram = int(avail_ram / vm_ram) if vm_ram > 0 else 999
        max_by_threads = int(avail_threads / vm_threads) if vm_threads > 0 else 999
        max_vms = min(max_by_vram, max_by_ram, max_by_threads)

        bottleneck = "VRAM" if max_vms == max_by_vram else "RAM" if max_vms == max_by_ram else "Threads"

        embed = discord.Embed(title="🖥️ VM Calculator", color=0x00D4AA)
        embed.add_field(
            name="Hardware",
            value=f"VRAM: {vram}GB | RAM: {ram}GB | Threads: {threads}",
            inline=False,
        )
        embed.add_field(
            name="VM Profile",
            value=f"VRAM: {vm_vram}GB | RAM: {vm_ram}GB | Threads: {vm_threads}",
            inline=False,
        )
        embed.add_field(
            name="Result",
            value=f"**{max_vms} VMs** (limited by {bottleneck})",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="compare", description="Compare used (OLX) vs new prices")
    @app_commands.describe(item="Filter by item name (optional)")
    async def compare(self, interaction: discord.Interaction, item: str | None = None):
        await interaction.response.defer()

        data = await hardware_api.get_price_comparison()
        if item:
            data = [d for d in data if item.lower() in d["item_name"].lower()]

        if not data:
            await interaction.followup.send("No price comparison data available.")
            return

        embed = discord.Embed(title="📊 Usado vs Novo", color=0x3498DB)

        for d in data[:10]:
            olx_min = d.get("olx_min")
            price_new = d.get("price_new")
            savings = d.get("savings_pct")

            olx_str = _format_price(olx_min) if olx_min else "—"
            new_str = _format_price(price_new) if price_new else "—"
            savings_str = f" | **-{savings}%**" if savings else ""

            embed.add_field(
                name=d["item_name"],
                value=(
                    f"🔵 OLX: {olx_str} ({d.get('olx_count', 0)} deals)\n"
                    f"🟢 Novo: {new_str}{savings_str}"
                ),
                inline=True,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="newprice", description="Check new prices from stores")
    @app_commands.describe(category="Category: gpu, cpu, ram, motherboard, ssd, psu")
    async def newprice(self, interaction: discord.Interaction, category: str = "gpu"):
        await interaction.response.defer()

        products = await hardware_api.get_new_prices(category, limit=10)
        if not products:
            await interaction.followup.send(f"No new prices found for '{category}'")
            return

        embed = discord.Embed(
            title=f"🛒 New Prices — {category.upper()}",
            color=0x2ECC71,
        )

        lines = []
        for p in products[:10]:
            price = _format_price(p["cash_price"])
            name = p["name"][:40]
            merchant = p.get("merchant", "")[:15]
            lines.append(f"**{price}** — {name}\n└ {merchant}")

        embed.description = "\n\n".join(lines)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="sync", description="Sync new prices from PCBuildWizard")
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer()
        result = await hardware_api.sync_new_prices()
        total = result.get("total_products", 0)
        manual = result.get("manual_prices_updated", 0)
        categories = result.get("categories", [])

        if total == 0:
            await interaction.followup.send("Sync failed or no products found.")
            return

        embed = discord.Embed(
            title=f"✅ Synced {total} products",
            color=0x2ECC71,
        )
        lines = []
        for c in categories:
            err = c.get("error", "")
            lines.append(f"**{c['category']}**: {c['products']} products{f' ⚠️ {err[:30]}' if err else ''}")
        if manual > 0:
            lines.append(f"\n📌 {manual} manual prices updated")
        embed.description = "\n".join(lines)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="status", description="System status (worker, scheduler, deals)")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()

        worker = await hardware_api.get_worker_status()
        scheduler = await hardware_api.get_scheduler_status()
        summary = await hardware_api.get_summary()

        total_deals = sum(s.get("count", 0) for s in summary)

        embed = discord.Embed(title="⚙️ System Status", color=0x95A5A6)
        embed.add_field(
            name="Worker",
            value="🟢 Online" if worker.get("online") else "🔴 Offline",
            inline=True,
        )
        embed.add_field(
            name="Scheduler",
            value="🟢 Running" if scheduler.get("running") else "🔴 Stopped",
            inline=True,
        )
        embed.add_field(
            name="Deals",
            value=f"{total_deals} active",
            inline=True,
        )

        if scheduler.get("jobs"):
            jobs_str = "\n".join(f"• {j['id']} ({j['interval']})" for j in scheduler["jobs"])
            embed.add_field(name="Scheduled Jobs", value=jobs_str, inline=False)

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hardware(bot))
