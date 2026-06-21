import os
import time

import httpx

_token: str | None = None
_expires_at: float = 0.0


async def get_token() -> str:
    global _token, _expires_at
    if _token and time.time() < _expires_at - 300:
        return _token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": os.environ["WXO_API_KEY"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
    _token = data["access_token"]
    _expires_at = time.time() + data.get("expires_in", 3600)
    return _token
