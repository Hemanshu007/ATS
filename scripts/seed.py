"""Seed script — creates test recruiter and candidate for quick testing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import async_session
from app.core.security import hash_password
from app.models.user import User
from app.models.company import Company
from app.models.recruiter import Recruiter
from app.models.candidate import Candidate

# Test credentials
RECRUITER_EMAIL = "alice@techcorp.com"
RECRUITER_PASSWORD = "recruiter123"
CANDIDATE_EMAIL = "hemanshu@gmail.com"
CANDIDATE_PASSWORD = "candidate123"


async def seed():
    async with async_session() as db:
        # Skip if already seeded
        existing = await db.scalar(select(User).where(User.email == RECRUITER_EMAIL))
        if existing:
            print("⚠️  Seed data already exists, skipping.")
            return

        # Company
        company = Company(name="TechCorp", industry="Technology", location="Bangalore")
        db.add(company)
        await db.flush()

        # Recruiter
        recruiter_user = User(email=RECRUITER_EMAIL, hashed_password=hash_password(RECRUITER_PASSWORD), role="recruiter")
        db.add(recruiter_user)
        await db.flush()
        recruiter = Recruiter(user_id=recruiter_user.id, company_id=company.id, name="Alice")
        db.add(recruiter)

        # Candidate
        candidate_user = User(email=CANDIDATE_EMAIL, hashed_password=hash_password(CANDIDATE_PASSWORD), role="candidate")
        db.add(candidate_user)
        await db.flush()
        candidate = Candidate(user_id=candidate_user.id, name="Hemanshu", phone="9876543210", location="Mumbai")
        db.add(candidate)

        await db.commit()
        print("✅ Seed data created:")
        print(f"   Recruiter: {RECRUITER_EMAIL}")
        print(f"   Candidate: {CANDIDATE_EMAIL}")
        print("   (Passwords in README.md)")


if __name__ == "__main__":
    asyncio.run(seed())
