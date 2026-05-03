from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.ai.prediction.model import prediction_service
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.scheduler import setup_scheduler
from app.db.init_db import bootstrap_admin
from app.db.session import check_database_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_admin()
    # Load XGBoost model nếu đã train
    prediction_service.load()
    # Start APScheduler (daily batch predictions at 02:00)
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} job(s)")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI Student Warning System API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    database_connected = await check_database_connection()
    return {
        "status": "ok" if database_connected else "degraded",
        "database": "connected" if database_connected else "disconnected",
        "environment": settings.APP_ENV,
    }