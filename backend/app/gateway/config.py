import os

from fastapi import HTTPException

_STAGE_ENV_VARS: dict[str, str] = {
    "admissions": "AGENT_ID_ADMISSIONS",
    "enrollment": "AGENT_ID_ENROLLMENT",
    "teaching_readiness_cohort": "AGENT_ID_TEACHING_READINESS_COHORT",
    "teaching_readiness_workload": "AGENT_ID_TEACHING_READINESS_WORKLOAD",
    "academic_risk_engagement": "AGENT_ID_ACADEMIC_RISK_ENGAGEMENT",
    "academic_risk_intervention": "AGENT_ID_ACADEMIC_RISK_INTERVENTION",
    "academic_risk_support": "AGENT_ID_ACADEMIC_RISK_SUPPORT",
    "progression": "AGENT_ID_PROGRESSION",
    "career": "AGENT_ID_CAREER",
}

VALID_STAGES = set(_STAGE_ENV_VARS)


def get_agent_id(stage: str) -> str:
    env_var = _STAGE_ENV_VARS.get(stage)
    if not env_var:
        raise HTTPException(status_code=422, detail=f"Unknown stage: {stage}")
    agent_id = os.getenv(env_var, "")
    if not agent_id:
        raise HTTPException(status_code=503, detail=f"Agent not configured for stage: {stage}")
    return agent_id
