"""
Events API (M6.4) — /api/v1/events

Admin endpoints:
- POST   /events                — tạo event
- GET    /events                — list (admin: tất cả)
- PUT    /events/{id}           — update
- DELETE /events/{id}           — xoá

Student endpoints:
- GET /events/me                — events match target_audience của SV
- GET /events/me/upcoming       — chỉ events sắp diễn ra (start_time >= now)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_student, get_db, require_admin
from app.models.event import EventType
from app.models.student import Student
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.services import event_manager

router = APIRouter(prefix="/events", tags=["events"])


# ─── Admin endpoints ──────────────────────────────────────────


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_event(
    payload: EventCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await event_manager.create_event(
        db, payload=payload, created_by=admin.id
    )


@router.get("", response_model=list[EventResponse])
async def admin_list_events(
    event_type: EventType | None = None,
    limit: int = Query(200, ge=1, le=500),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await event_manager.list_events_for_admin(
        db, event_type=event_type, limit=limit
    )


@router.put("/{event_id}", response_model=EventResponse)
async def admin_update_event(
    event_id: UUID,
    payload: EventUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    event = await event_manager.update_event(db, event_id=event_id, payload=payload)
    if not event:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự kiện")
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_event(
    event_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ok = await event_manager.delete_event(db, event_id=event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự kiện")
    return None


# ─── Student endpoints ────────────────────────────────────────


@router.get("/me", response_model=list[EventResponse])
async def list_my_events(
    limit: int = Query(50, ge=1, le=200),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await event_manager.list_events_for_student(
        db, student=student, only_upcoming=False, limit=limit
    )


@router.get("/me/upcoming", response_model=list[EventResponse])
async def list_my_upcoming_events(
    limit: int = Query(20, ge=1, le=100),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await event_manager.list_events_for_student(
        db, student=student, only_upcoming=True, limit=limit
    )
