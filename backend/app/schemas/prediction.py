from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel

from app.models.prediction import RiskLevel


class PredictionResponse(BaseModel):
    id: UUID
    student_id: UUID
    semester: str
    risk_score: float
    risk_level: RiskLevel
    risk_factors: Optional[dict[str, Any]]
    predicted_courses: Optional[list[Any]]
    created_at: datetime

    model_config = {"from_attributes": True}
