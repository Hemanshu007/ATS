import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    location: str | None

    class Config:
        from_attributes = True


class RecruiterOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    company_id: uuid.UUID

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    user: UserOut
    profile: CandidateOut | RecruiterOut
