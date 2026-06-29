import os
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.gateway import fallback, iam, orchestrate
from app.gateway.config import get_agent_id

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationRequest(BaseModel):
    entity_id: str
    entity_type: Literal["student", "cohort"]
    action: str


@router.post("/{stage}")
async def recommend(stage: str, body: RecommendationRequest):
    if os.getenv("AI_MODE", "live") == "scripted":
        return fallback.get(stage)
    agent_id = get_agent_id(stage)
    token = await iam.get_token()
    run_id = await orchestrate.start_run(agent_id, token, body.model_dump())
    run = await orchestrate.poll_run(agent_id, run_id, token)
    if run["status"] in ("failed", "expired"):
        return fallback.get(stage)
    return {
        "stage": stage,
        "result": run["output"]["result"],
        "source": "live",
    }
