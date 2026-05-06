from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    chatbot,
    courses,
    documents,
    events,
    notifications,
    predictions,
    students,
    study_plan,
    warnings,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(courses.router)
api_router.include_router(predictions.router)
api_router.include_router(chatbot.router)
api_router.include_router(documents.router)
# ─── M6 ────────────────────────────────────────────
api_router.include_router(warnings.router)
api_router.include_router(notifications.router)
api_router.include_router(study_plan.router)
api_router.include_router(events.router)
# ─── M7 ────────────────────────────────────────────
api_router.include_router(admin.router)
