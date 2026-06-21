import asyncio
import os

import httpx

POLL_INTERVAL: float = 1.0  # seconds between status checks; override in tests


async def start_run(agent_id: str, token: str, payload: dict) -> str:
    base = os.environ["WXO_BASE_URL"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/agents/{agent_id}/runs",
            json={"input": payload},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
    return resp.json()["run_id"]


async def poll_run(
    agent_id: str, run_id: str, token: str, *, timeout: int = 30
) -> dict:
    base = os.environ["WXO_BASE_URL"]
    deadline = asyncio.get_running_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                f"{base}/agents/{agent_id}/runs/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status in ("completed", "failed", "expired"):
                return data
            if asyncio.get_running_loop().time() >= deadline:
                return {"status": "expired", "output": {}}
            await asyncio.sleep(POLL_INTERVAL)
