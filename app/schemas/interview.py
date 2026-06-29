import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InterviewCreate(BaseModel):
    application_id: uuid.UUID
    round_number: int
    scheduled_at: datetime | None = None
    conducted_by: uuid.UUID | None = None


class OutcomeUpdate(BaseModel):
    outcome: Literal["pending", "pass", "fail"]
    notes: str | None = None


class InterviewOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    round_number: int
    scheduled_at: datetime | None
    conducted_by: uuid.UUID | None
    outcome: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
