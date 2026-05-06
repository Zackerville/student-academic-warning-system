"""
Courses API — /api/v1/courses
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.models.course import Course
from app.models.user import User
from app.schemas.course import CourseCreate, CourseResponse

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Course).order_by(Course.course_code)
    if search:
        q = q.where(
            Course.course_code.ilike(f"%{search}%")
            | Course.name.ilike(f"%{search}%")
        )
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=CourseResponse, status_code=201)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    existing = await db.execute(
        select(Course).where(Course.course_code == payload.course_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Mã môn học đã tồn tại")

    course = Course(**payload.model_dump())
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(course_id: str, db: AsyncSession = Depends(get_db)):
    from uuid import UUID
    try:
        uid = UUID(course_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="course_id không hợp lệ")
    course = await db.get(Course, uid)
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học")
    return course
