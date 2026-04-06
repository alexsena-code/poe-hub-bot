"""Background task that watches for good deals and sends alerts."""
import logging
from discord.ext import tasks, commands
import discord

from services import hardware_api

log = logging.getLogger("deal-watcher")


class DealWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot, alert_channel_id: int | None = None):
        self.bot = bot
        self.alert_channel_id = alert_channel_id
        self._seen_deals: set[str] = set()  # external_ids already alerted
        if alert_channel_id:
            self.check_deals.start()

    def cog_unload(self):
        self.check_deals.cancel()

    @tasks.loop(minutes=30)
    async def check_deals(self):
        """Check for new deals below max_price and alert."""
        if not self.alert_channel_id:
            return

        channel = self.bot.get_channel(self.alert_channel_id)
        if not channel:
            log.warning("Alert channel %s not found", self.alert_channel_id)
            return

        items = await hardware_api.get_items()
        deals = await hardware_api.get_deals(limit=200)

        for deal in deals:
            deal_key = f"{deal['source']}:{deal.get('id', '')}"
            if deal_key in self._seen_deals:
                continue

            # Find matching item config
            item = next((i for i in items if i["name"] == deal["item_name"]), None)
            if not item:
                continue

            max_price = item["max_price"]
            if deal["price"] <= max_price * 0.85:  # 15% below target
                self._seen_deals.add(deal_key)

                savings = round((1 - deal["price"] / max_price) * 100)
                embed = discord.Embed(
                    title=f"🔥 {deal['item_name']} por R$ {deal['price']:,.0f}",
                    url=deal.get("url", ""),
                    color=0xFF4500,
                    description=(
                        f"**{deal['title']}**\n"
                        f"📍 {deal.get('location', 'N/A')}\n"
                        f"💰 Target: R$ {max_price:,.0f} | **-{savings}%**"
                    ),
                )
                if deal.get("image_url"):
                    embed.set_thumbnail(url=deal["image_url"])
                embed.set_footer(text=f"{deal['source'].upper()} • {deal.get('found_at', '')[:10]}")

                await channel.send(embed=embed)

        # Keep seen deals under 5000
        if len(self._seen_deals) > 5000:
            self._seen_deals = set(list(self._seen_deals)[-2000:])

    @check_deals.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    import os
    channel_id = os.getenv("ALERT_CHANNEL_ID")
    cid = int(channel_id) if channel_id else None
    await bot.add_cog(DealWatcher(bot, cid))
