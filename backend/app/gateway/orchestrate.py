import asyncio
import json
import os

import httpx

POLL_INTERVAL: float = 1.0  # seconds between status checks; override in tests


async def start_run(agent_id: str, token: str, payload: dict) -> str:
    base = os.environ["WXO_BASE_URL"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/v1/orchestrate/runs",
            json={
                "message": {"role": "user", "content": json.dumps(payload)},
                "agent_id": agent_id,
                "capture_logs": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
    return resp.json()["run_id"]


def _extract_result_text(data: dict) -> str:
    content = data["result"]["data"]["message"]["content"]
    return content[0]["text"]


async def poll_run(
    agent_id: str, run_id: str, token: str, *, timeout: int = 30
) -> dict:
    base = os.environ["WXO_BASE_URL"]
    deadline = asyncio.get_running_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                f"{base}/v1/orchestrate/runs/{run_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "completed":
                return {"status": "completed", "output": {"result": _extract_result_text(data)}}
            if status in ("failed", "cancelled"):
                return {"status": "failed", "output": {}}
            if asyncio.get_running_loop().time() >= deadline:
                return {"status": "expired", "output": {}}
            await asyncio.sleep(POLL_INTERVAL)
