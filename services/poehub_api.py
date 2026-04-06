"""Client for the PoE Hub API (NestJS content engine)."""
import os
import httpx

BASE = os.getenv("POEHUB_API_URL", "https://api.pathoftrade.net")
API_KEY = os.getenv("POEHUB_API_KEY", "")

HEADERS = {"x-api-key": API_KEY} if API_KEY else {}


async def get_llm_logs(limit: int = 10):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/llm-logs", params={"limit": limit}, headers=HEADERS)
        return r.json() if r.status_code == 200 else []


async def get_llm_costs(days: int = 7):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/llm-logs/costs", params={"days": days}, headers=HEADERS)
        return r.json() if r.status_code == 200 else {}


async def get_knowledge_stats():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/knowledge/stats", headers=HEADERS)
        return r.json() if r.status_code == 200 else {}


async def ask_question(question: str):
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"{BASE}/knowledge/answer",
            json={"question": question, "queryType": "qa"},
            headers=HEADERS,
        )
        return r.json() if r.status_code == 200 else {"answer": "API error"}
