"""
APScheduler setup — chạy job định kỳ trong-process.

Jobs:
  - predictions_batch:   02:00 AM mỗi ngày, predict cho mọi SV → lưu predictions table
  - deadline_reminders:  07:00 AM mỗi ngày, gửi nhắc nhở SV cho event bắt buộc trong 24h tới
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import and_, or_, select

from app.ai.prediction.model import prediction_service
from app.db.session import AsyncSessionLocal
from app.models.event import Event, TargetAudience
from app.models.notification import Notification, NotificationType
from app.models.student import Student


async def run_predictions_batch():
    """Job: predict cho mọi SV. Log progress + lưu predictions table."""
    if not prediction_service.is_loaded:
        logger.warning("Prediction model chưa load — skip batch")
        return
    logger.info("Starting predictions batch run")
    async with AsyncSessionLocal() as db:
        count = await prediction_service.predict_batch(db, only_synthetic=False)
    logger.info(f"Predictions batch done: {count} students predicted")


async def run_deadline_reminders():
    """Job: gửi notification nhắc SV về event bắt buộc bắt đầu trong 24h tới."""
    now = datetime.now(tz=timezone.utc)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Event).where(
                and_(
                    Event.is_mandatory == True,  # noqa: E712
                    Event.start_time >= window_start,
                    Event.start_time <= window_end,
                )
            )
        )
        events = list(result.scalars().all())

        if not events:
            logger.info("Deadline reminders: no mandatory events in 24h window")
            return

        for event in events:
            # Resolve matching students
            if event.target_audience == TargetAudience.all:
                students_result = await db.execute(select(Student))
            elif event.target_audience == TargetAudience.faculty_specific:
                students_result = await db.execute(
                    select(Student).where(Student.faculty == (event.target_value or ""))
                )
            elif event.target_audience == TargetAudience.cohort_specific:
                cohort_val = event.target_value or ""
                if cohort_val.isdigit():
                    students_result = await db.execute(
                        select(Student).where(Student.cohort == int(cohort_val))
                    )
                else:
                    continue
            else:
                continue

            students = list(students_result.scalars().all())
            start_str = event.start_time.strftime("%H:%M ngày %d/%m/%Y")
            for student in students:
                db.add(
                    Notification(
                        student_id=student.id,
                        type=NotificationType.reminder,
                        title=f"Nhắc nhở: {event.title}",
                        content=f"Sự kiện bắt buộc sẽ diễn ra lúc {start_str}.\n{event.description or ''}".strip(),
                    )
                )

        await db.commit()
        logger.info(f"Deadline reminders sent for {len(events)} event(s)")


def setup_scheduler() -> AsyncIOScheduler:
    """Tạo scheduler + register jobs. Caller phải gọi .start() và .shutdown()."""
    scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

    scheduler.add_job(
        run_predictions_batch,
        trigger=CronTrigger(hour=2, minute=0),
        id="predictions_batch_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        run_deadline_reminders,
        trigger=CronTrigger(hour=7, minute=0),
        id="deadline_reminders_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    return scheduler
