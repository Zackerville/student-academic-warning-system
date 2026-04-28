import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.user import RegisterRequest, Token, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # ─── Kiểm tra email & MSSV trùng ─────────────────────────
    email_exists = await db.execute(select(User).where(User.email == payload.email))
    if email_exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    mssv_exists = await db.execute(select(Student).where(Student.mssv == payload.mssv))
    if mssv_exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="MSSV đã được sử dụng")

    # ─── Tạo User ────────────────────────────────────────────
    user = User(
        id=uuid.uuid4(),
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.student,
    )
    db.add(user)
    await db.flush()

    # ─── Tạo Student profile ─────────────────────────────────
    student = Student(
        id=uuid.uuid4(),
        user_id=user.id,
        mssv=payload.mssv,
        full_name=payload.full_name,
        faculty=payload.faculty,
        major=payload.major,
        cohort=payload.cohort,
    )
    db.add(student)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
