"""
Event Manager Service (M6.4) — CRUD events + filter theo SV.

Logic chính:
- Admin CRUD đầy đủ
- SV chỉ xem events match target_audience:
  - all                → mọi SV
  - faculty_specific   → SV cùng faculty (target_value == student.faculty)
  - cohort_specific    → SV cùng cohort (target_value == str(student.cohort))
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventType, TargetAudience
from app.models.notification import Notification, NotificationType
from app.models.student import Student
from app.schemas.event import EventCreate, EventUpdate


async def create_event(
    db: AsyncSession, *, payload: EventCreate, created_by: UUID
) -> Event:
    event = Event(
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        target_audience=payload.target_audience,
        target_value=payload.target_value,
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_mandatory=payload.is_mandatory,
        created_by=created_by,
    )
    db.add(event)
    await db.flush()

    students = await _matching_students_for_event(db, event)
    for student in students:
        db.add(
            Notification(
                student_id=student.id,
                type=NotificationType.event,
                title=f"Sự kiện mới: {event.title}",
                content=_event_notification_content(event),
            )
        )

    await db.commit()
    await db.refresh(event)
    return event


async def update_event(
    db: AsyncSession, *, event_id: UUID, payload: EventUpdate
) -> Optional[Event]:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, *, event_id: UUID) -> bool:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return False
    await db.delete(event)
    await db.commit()
    return True


async def list_events_for_admin(
    db: AsyncSession,
    *,
    event_type: Optional[EventType] = None,
    from_time: Optional[datetime] = None,
    limit: int = 200,
) -> list[Event]:
    stmt = select(Event).order_by(Event.start_time.desc()).limit(limit)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if from_time:
        stmt = stmt.where(Event.start_time >= from_time)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_events_for_student(
    db: AsyncSession,
    *,
    student: Student,
    only_upcoming: bool = False,
    limit: int = 50,
) -> list[Event]:
    """
    Filter events theo target_audience match SV.
    only_upcoming = True → chỉ event start_time >= now hoặc ongoing.
    """
    stmt = (
        select(Event)
        .where(_student_event_filter(student))
        .order_by(Event.start_time.asc())
        .limit(limit)
    )
    if only_upcoming:
        now = datetime.now(tz=timezone.utc)
        stmt = stmt.where(
            or_(
                Event.start_time >= now,
                and_(Event.start_time < now, Event.end_time >= now),
            )
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_event(db: AsyncSession, event_id: UUID) -> Optional[Event]:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


def event_type_label(event_type: EventType) -> str:
    return {
        EventType.exam: "Thi cử",
        EventType.submission: "Nộp bài / hạn chót",
        EventType.activity: "Hoạt động sinh viên",
        EventType.evaluation: "Đánh giá / khảo sát",
    }.get(event_type, "Sự kiện")


def format_event_time_vi(dt: Optional[datetime]) -> Optional[str]:
    """Format ISO datetime → "HH:mm dd/MM/YYYY" tiếng Việt cho email."""
    if not dt:
        return None
    return dt.strftime("%H:%M ngày %d/%m/%Y")


def _student_event_filter(student: Student):
    return or_(
        Event.target_audience == TargetAudience.all,
        and_(
            Event.target_audience == TargetAudience.faculty_specific,
            Event.target_value == (student.faculty or ""),
        ),
        and_(
            Event.target_audience == TargetAudience.cohort_specific,
            Event.target_value == str(student.cohort or ""),
        ),
    )


def _event_student_filter(event: Event):
    if event.target_audience == TargetAudience.faculty_specific:
        return Student.faculty == (event.target_value or "")
    if event.target_audience == TargetAudience.cohort_specific:
        return Student.cohort == int(event.target_value) if str(event.target_value or "").isdigit() else Student.id.is_(None)
    return True


async def _matching_students_for_event(db: AsyncSession, event: Event) -> list[Student]:
    stmt = select(Student)
    student_filter = _event_student_filter(event)
    if student_filter is not True:
        stmt = stmt.where(student_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _event_notification_content(event: Event) -> str:
    lines = [
        f"Loại: {event_type_label(event.event_type)}",
        f"Bắt đầu: {format_event_time_vi(event.start_time)}",
    ]
    if event.end_time:
        lines.append(f"Kết thúc: {format_event_time_vi(event.end_time)}")
    if event.is_mandatory:
        lines.append("Đây là sự kiện bắt buộc.")
    if event.description:
        lines.append("")
        lines.append(event.description)
    return "\n".join(lines)
