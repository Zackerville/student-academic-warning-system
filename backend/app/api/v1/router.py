from fastapi import APIRouter

from app.api.v1 import auth, chatbot, courses, documents, predictions, students

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(courses.router)
api_router.include_router(predictions.router)
api_router.include_router(chatbot.router)
api_router.include_router(documents.router)
