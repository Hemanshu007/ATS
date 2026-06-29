import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(max_length=150)
    description: str = Field(max_length=5000)
    location: str | None = Field(default=None, max_length=100)
    job_type: Literal["onsite", "remote", "hybrid"] = "onsite"


class JobStatusUpdate(BaseModel):
    status: Literal["open", "closed"]


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    location: str | None
    job_type: str
    status: str
    company: CompanyOut
    created_at: datetime

    class Config:
        from_attributes = True
