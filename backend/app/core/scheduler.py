"""
APScheduler setup — chạy job định kỳ trong-process.

Jobs:
  - predictions_batch: 02:00 AM mỗi ngày, predict cho mọi SV → lưu predictions table
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.ai.prediction.model import prediction_service
from app.db.session import AsyncSessionLocal


async def run_predictions_batch():
    """Job: predict cho mọi SV. Log progress + lưu predictions table."""
    if not prediction_service.is_loaded:
        logger.warning("Prediction model chưa load — skip batch")
        return
    logger.info("Starting predictions batch run")
    async with AsyncSessionLocal() as db:
        count = await prediction_service.predict_batch(db, only_synthetic=False)
    logger.info(f"Predictions batch done: {count} students predicted")


def setup_scheduler() -> AsyncIOScheduler:
    """Tạo scheduler + register jobs. Caller phải gọi .start() và .shutdown()."""
    scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

    scheduler.add_job(
        run_predictions_batch,
        trigger=CronTrigger(hour=2, minute=0),  # 02:00 mỗi ngày
        id="predictions_batch_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    return scheduler
