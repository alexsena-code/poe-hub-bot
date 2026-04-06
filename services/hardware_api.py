"""Client for the Hardware Deals API."""
import os
import httpx

BASE = os.getenv("HARDWARE_API_URL", "https://api.pathoftrade.net/hardware-api")


async def get_deals(item_name: str | None = None, limit: int = 10):
    async with httpx.AsyncClient(timeout=15) as c:
        params = {"limit": limit}
        if item_name:
            params["item_name"] = item_name
        r = await c.get(f"{BASE}/api/deals", params=params)
        return r.json() if r.status_code == 200 else []


async def get_summary():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/api/deals/summary")
        return r.json() if r.status_code == 200 else []


async def get_items():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/api/items")
        return r.json() if r.status_code == 200 else []


async def trigger_scrape(item_id: int | None = None):
    async with httpx.AsyncClient(timeout=120) as c:
        body = {"item_id": item_id} if item_id else {}
        r = await c.post(f"{BASE}/api/scrape", json=body)
        return r.json() if r.status_code == 200 else {"status": "error"}


async def get_worker_status():
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{BASE}/api/worker/status")
        return r.json() if r.status_code == 200 else {"online": False}


async def get_price_comparison():
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{BASE}/api/analytics/price-comparison")
        return r.json() if r.status_code == 200 else []


async def get_new_prices(category: str, limit: int = 10):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{BASE}/api/new-prices/{category}", params={"limit": limit})
        return r.json() if r.status_code == 200 else []


async def sync_new_prices():
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{BASE}/api/sync-new-prices")
        return r.json() if r.status_code == 200 else {"status": "error"}


async def get_scheduler_status():
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{BASE}/api/scheduler/status")
        return r.json() if r.status_code == 200 else {"running": False}
