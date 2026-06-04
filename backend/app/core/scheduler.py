"""
APScheduler setup — chạy job định kỳ trong-process.

Jobs:
  - predictions_batch:   02:00 AM mỗi ngày, predict cho mọi SV → lưu predictions table
  - deadline_reminders:  07:00 AM mỗi ngày, gửi nhắc nhở SV cho event bắt buộc trong 24h tới
  - exam_reminders:      07:00 AM mỗi ngày, gửi nhắc nhở thi từ exam_schedule_json trong 24h tới
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import and_, or_, select

from app.ai.prediction.model import prediction_service
from app.db.session import AsyncSessionLocal
from app.models.event import Event, TargetAudience
from app.models.notification import Notification, NotificationType
from app.models.student import Student

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


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


async def run_exam_reminders():
    """Job: gửi notification nhắc SV về lịch thi (từ exam_schedule_json) trong 24h tới.

    Window: bây giờ → +25h (job 07:00 VN → bắt kịp thi cùng ngày lẫn sáng hôm sau).
    Dedup: skip nếu đã gửi notification cùng title trong 23h gần nhất (tránh spam).
    """
    now_utc = datetime.now(tz=timezone.utc)
    window_end_utc = now_utc + timedelta(hours=25)
    dedup_cutoff = now_utc - timedelta(hours=23)

    async with AsyncSessionLocal() as db:
        # Lấy mọi SV có exam_schedule_json
        result = await db.execute(
            select(Student).where(Student.exam_schedule_json.isnot(None))
        )
        students = list(result.scalars().all())

        notification_count = 0
        for student in students:
            exams = (student.exam_schedule_json or {}).get("exams", [])
            for exam in exams:
                exam_date_str: str | None = exam.get("exam_date")   # "2026-05-25"
                start_time_str: str | None = exam.get("start_time") # "07:00"
                if not exam_date_str or not start_time_str:
                    continue

                try:
                    y, mo, d = map(int, exam_date_str.split("-"))
                    h, mi = map(int, start_time_str.split(":"))
                    exam_dt_utc = datetime(y, mo, d, h, mi, tzinfo=_VN_TZ).astimezone(timezone.utc)
                except Exception:
                    continue

                if not (now_utc <= exam_dt_utc <= window_end_utc):
                    continue

                course_code = exam.get("course_code", "")
                exam_type = exam.get("exam_type", "")
                type_label = "Cuối kỳ" if exam_type == "CK" else "Giữa kỳ"
                room = exam.get("room", "")
                campus = exam.get("campus", "")
                duration = exam.get("duration_min", 0)
                course_name = exam.get("course_name", "")
                title = f"Nhắc thi {type_label}: {course_code}"

                # Dedup — skip nếu đã gửi cùng title gần đây
                dup = (await db.execute(
                    select(Notification).where(
                        and_(
                            Notification.student_id == student.id,
                            Notification.title == title,
                            Notification.sent_at >= dedup_cutoff,
                        )
                    )
                )).scalar_one_or_none()
                if dup:
                    continue

                content_parts = [
                    f"Bạn có lịch thi {type_label} môn {course_code}"
                    + (f" — {course_name}" if course_name else ""),
                    f"🕐 {start_time_str} ngày {exam_date_str}",
                ]
                if room:
                    content_parts.append(f"📍 Phòng {room}" + (f" ({campus})" if campus else ""))
                if duration:
                    content_parts.append(f"⏱ Thời gian thi: {duration} phút")
                content_parts.append("Chúc bạn thi tốt! 💪")

                db.add(Notification(
                    student_id=student.id,
                    type=NotificationType.reminder,
                    title=title,
                    content="\n".join(content_parts),
                ))
                notification_count += 1

        await db.commit()
        logger.info(f"Exam reminders: {notification_count} notification(s) sent to {len(students)} student(s)")


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

    scheduler.add_job(
        run_exam_reminders,
        trigger=CronTrigger(hour=7, minute=0),
        id="exam_reminders_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    return scheduler
