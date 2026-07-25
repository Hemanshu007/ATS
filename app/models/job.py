import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(100))
    job_type: Mapped[str] = mapped_column(String(20), default="onsite")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("recruiters.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    embedding = mapped_column(Vector(1536), nullable=True)

    company = relationship("Company", back_populates="jobs")
    creator = relationship("Recruiter", back_populates="jobs")
    applications = relationship("Application", back_populates="job")
