"""Import write_tools.yaml into watsonx Orchestrate.

Usage:
    python orchestrate/import_tools.py

Required env vars (set in .env):
    ORCHESTRATE_BASE_URL  — e.g. https://api.us-south.assistant.watson.cloud.ibm.com
    IBM_CLOUD_API_KEY     — IBM Cloud API key
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx

TOOLS_DIR = Path(__file__).parent / "tools"
WRITE_TOOLS_PATH = TOOLS_DIR / "write_tools.yaml"


async def get_iam_token(api_key: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
    return resp.json()["access_token"]


async def import_tool(base_url: str, token: str, spec_path: Path) -> dict:
    spec_yaml = spec_path.read_text()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}/tools",
            content=spec_yaml.encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/yaml",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
    return resp.json()


async def main() -> None:
    base_url = os.environ.get("ORCHESTRATE_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("IBM_CLOUD_API_KEY", "")

    if not base_url or not api_key:
        print("ERROR: ORCHESTRATE_BASE_URL and IBM_CLOUD_API_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    if not WRITE_TOOLS_PATH.exists():
        print(f"ERROR: {WRITE_TOOLS_PATH} not found", file=sys.stderr)
        sys.exit(1)

    print("Fetching IAM token…")
    token = await get_iam_token(api_key)

    print(f"Importing {WRITE_TOOLS_PATH.name} → {base_url}/tools …")
    result = await import_tool(base_url, token, WRITE_TOOLS_PATH)

    tool_id = result.get("id") or result.get("tool_id") or "(unknown)"
    print(f"Done. Tool ID: {tool_id}")
    print("write_tools are now live in Orchestrate alongside read_tools.")


if __name__ == "__main__":
    asyncio.run(main())
