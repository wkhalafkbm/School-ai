import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WorkflowItem

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


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


@router.get("", response_model=list[WorkflowItemResponse])
def list_workflows(db: Session = Depends(get_db)):
    return db.query(WorkflowItem).all()


@router.post("", response_model=WorkflowItemResponse, status_code=201)
def create_workflow_item(body: WorkflowItemCreate, db: Session = Depends(get_db)):
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
        data_source="demo",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=WorkflowItemResponse)
def update_workflow_item(item_id: str, body: WorkflowItemPatch, db: Session = Depends(get_db)):
    item = db.query(WorkflowItem).filter(WorkflowItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Workflow item {item_id!r} not found")
    if body.status is not None:
        item.status = body.status
    if body.due_date is not None:
        item.due_date = body.due_date
    db.commit()
    db.refresh(item)
    return item
