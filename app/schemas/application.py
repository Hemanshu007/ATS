import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

APPLICATION_STATUSES = Literal["applied", "screening", "interview", "offer", "hired", "rejected"]


class StatusUpdate(BaseModel):
    status: APPLICATION_STATUSES
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    document_id: uuid.UUID
    current_status: str
    applied_at: datetime

    class Config:
        from_attributes = True


class StatusHistoryOut(BaseModel):
    status: str
    changed_by: uuid.UUID
    changed_at: datetime
    notes: str | None

    class Config:
        from_attributes = True


class NoteCreate(BaseModel):
    content: str = Field(max_length=5000)


class NoteOut(BaseModel):
    id: uuid.UUID
    content: str
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
