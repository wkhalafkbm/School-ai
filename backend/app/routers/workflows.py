import hashlib
import json
import time
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WorkflowItem
from app.stages import STAGES, WORKFLOW_STATUSES

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# Suppresses duplicate create_workflow_item tool calls an agent makes within a
# single run (see issue #53). Keyed on a hash of the request body since the
# Orchestrate write-tool contract carries no run/session identifier.
_DEDUPE_WINDOW_SECONDS = 300
_recent_creates: dict[str, tuple[str, float]] = {}


class WorkflowItemResponse(BaseModel):
    id: str
    stage: Optional[str]
    trigger: Optional[str]
    owner_name: Optional[str]
    owner_role: Optional[str]
    status: Optional[str]
    due_date: Optional[date]
    description: Optional[str]
    student_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WorkflowItemCreate(BaseModel):
    stage: str
    trigger: str
    owner_name: str
    owner_role: str
    status: str
    due_date: Optional[date] = None
    description: str
    student_id: Optional[str] = None


class WorkflowItemPatch(BaseModel):
    status: Optional[str] = None
    due_date: Optional[date] = None


def _validate(field: str, value: str, vocabulary: frozenset[str]) -> None:
    """
    A stage or status outside the vocabulary is a row no page will ever show
    (issue #68), so reject it here rather than store something invisible. The
    error names the whole vocabulary — the caller is usually an agent, and the
    list is the only correction it gets.
    """
    if value not in vocabulary:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown {field}: {value!r}. "
                f"Valid values: {', '.join(sorted(vocabulary))}."
            ),
        )


@router.get("", response_model=list[WorkflowItemResponse])
def list_workflows(db: Session = Depends(get_db)):
    return db.query(WorkflowItem).all()


@router.post("", response_model=WorkflowItemResponse, status_code=201)
def create_workflow_item(body: WorkflowItemCreate, db: Session = Depends(get_db)):
    _validate("stage", body.stage, STAGES)
    _validate("status", body.status, WORKFLOW_STATUSES)

    now = time.monotonic()
    for cached_key, (_, created_at) in list(_recent_creates.items()):
        if now - created_at > _DEDUPE_WINDOW_SECONDS:
            del _recent_creates[cached_key]

    key = hashlib.sha256(
        json.dumps(body.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()

    cached = _recent_creates.get(key)
    if cached is not None:
        return db.query(WorkflowItem).filter(WorkflowItem.id == cached[0]).first()

    item = WorkflowItem(
        id=str(uuid.uuid4()),
        stage=body.stage,
        trigger=body.trigger,
        owner_name=body.owner_name,
        owner_role=body.owner_role,
        status=body.status,
        due_date=body.due_date,
        description=body.description,
        student_id=body.student_id,
        created_date=date.today(),
        data_source="demo",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    _recent_creates[key] = (item.id, now)
    return item


@router.patch("/{item_id}", response_model=WorkflowItemResponse)
def update_workflow_item(item_id: str, body: WorkflowItemPatch, db: Session = Depends(get_db)):
    item = db.query(WorkflowItem).filter(WorkflowItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Workflow item {item_id!r} not found")
    if body.status is not None:
        _validate("status", body.status, WORKFLOW_STATUSES)
        item.status = body.status
    if body.due_date is not None:
        item.due_date = body.due_date
    db.commit()
    db.refresh(item)
    return item
