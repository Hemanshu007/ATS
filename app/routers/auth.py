from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, DUMMY_HASH
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.candidate import Candidate
from app.models.recruiter import Recruiter
from app.models.company import Company
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user import MeResponse, UserOut, CandidateOut, RecruiterOut

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password), role=body.role)
    db.add(user)
    await db.flush()

    if body.role == "recruiter":
        if not body.company_name:
            raise HTTPException(status_code=400, detail="company_name required for recruiter")
        company = await db.scalar(select(Company).where(Company.name == body.company_name))
        if not company:
            company = Company(name=body.company_name)
            db.add(company)
            await db.flush()
        recruiter = Recruiter(user_id=user.id, company_id=company.id, name=body.name)
        db.add(recruiter)
    else:
        candidate = Candidate(user_id=user.id, name=body.name)
        db.add(candidate)

    await db.commit()
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user:
        # Timing-safe: run bcrypt even when user doesn't exist
        verify_password("dummy", DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_out = UserOut.model_validate(user)
    if user.role == "recruiter":
        recruiter = await db.scalar(select(Recruiter).where(Recruiter.user_id == user.id))
        return MeResponse(user=user_out, profile=RecruiterOut.model_validate(recruiter))
    else:
        candidate = await db.scalar(select(Candidate).where(Candidate.user_id == user.id))
        return MeResponse(user=user_out, profile=CandidateOut.model_validate(candidate))
