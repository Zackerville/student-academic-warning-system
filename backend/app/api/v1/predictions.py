"""
Predictions API — D1, D2, D3 endpoints.

Endpoints:
  GET  /predictions/me                — Risk score + factors + course predict (latest)
  GET  /predictions/me/history        — Lịch sử risk score (cho chart)
  POST /predictions/me/refresh        — Force re-predict cho chính SV
  POST /predictions/me/simulate       — What-if: predict với điểm giả định (không lưu)
  POST /predictions/batch-run         — [Admin] Trigger batch predict tất cả
"""
from __future__ import annotations

import copy
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.prediction.features import FEATURE_NAMES, FEATURE_VERSION, extract_features
from app.ai.prediction.model import prediction_service, risk_score_to_level, _apply_early_warning_calibration
from app.core.deps import get_current_student, get_db, require_admin
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.prediction import Prediction
from app.models.student import Student
from app.services import warning_engine
from app.services.gpa_calculator import score_to_grade_letter

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _features_match(cached: dict, current: dict) -> bool:
    """Return False when cached SHAP reasons were built from stale features."""
    for name in FEATURE_NAMES:
        if name not in cached:
            return False
        try:
            cached_value = float(cached[name])
            current_value = float(current[name])
        except (TypeError, ValueError, KeyError):
            return False
        if abs(cached_value - current_value) > 1e-6:
            return False
    return True


def _serialize_prediction(p: Prediction) -> dict:
    return {
        "id": str(p.id),
        "semester": p.semester,
        "risk_score": round(p.risk_score, 4),
        "risk_level": p.risk_level.value,
        "risk_factors": (p.risk_factors or {}).get("factors", []),
        "predicted_courses": p.predicted_courses or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/me")
async def get_my_prediction(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy prediction mới nhất của SV.
    Auto re-predict nếu prediction cached cũ hơn enrollment update mới nhất
    (tức là SV vừa import myBK / nhập điểm).
    """
    if not prediction_service.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="AI model chưa được train hoặc load. Liên hệ admin.",
        )

    await warning_engine.sync_current_warning_level(db, student)

    # Tìm prediction mới nhất
    result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student.id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    # Check xem có enrollment nào update sau prediction cuối cùng không
    needs_refresh = latest is None
    if latest is not None:
        risk_factors = latest.risk_factors or {}
        if risk_factors.get("feature_version") != FEATURE_VERSION:
            needs_refresh = True

        latest_enrollment_update = await db.execute(
            select(func.max(Enrollment.updated_at))
            .where(Enrollment.student_id == student.id)
        )
        max_update = latest_enrollment_update.scalar_one_or_none()
        if max_update and latest.created_at and max_update > latest.created_at:
            needs_refresh = True

        if not needs_refresh:
            cached_features = risk_factors.get("features")
            if not isinstance(cached_features, dict):
                needs_refresh = True
            else:
                current_enrollments = await db.execute(
                    select(Enrollment)
                    .where(Enrollment.student_id == student.id)
                    .options(selectinload(Enrollment.course))
                )
                current_features = await extract_features(
                    student,
                    current_enrollments.scalars().all(),
                )
                if not _features_match(cached_features, current_features):
                    needs_refresh = True

    if needs_refresh:
        latest = await prediction_service.predict_for_student(student, db, save=True)
        if latest is None:
            raise HTTPException(
                status_code=422,
                detail="Chưa đủ dữ liệu để dự đoán. Hãy import bảng điểm trước.",
            )

    return _serialize_prediction(latest)


@router.get("/me/history")
async def get_my_prediction_history(
    limit: int = 30,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Lịch sử risk score qua thời gian (dùng cho chart)."""
    result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student.id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    return [
        {
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "semester": p.semester,
            "risk_score": round(p.risk_score, 4),
            "risk_level": p.risk_level.value,
        }
        for p in reversed(history)
    ]


@router.post("/me/refresh")
async def refresh_my_prediction(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Force re-predict cho chính SV (vd sau khi nhập điểm mới)."""
    if not prediction_service.is_loaded:
        raise HTTPException(status_code=503, detail="AI model chưa load")
    await warning_engine.sync_current_warning_level(db, student)
    pred = await prediction_service.predict_for_student(student, db, save=True)
    if pred is None:
        raise HTTPException(
            status_code=422,
            detail="Chưa đủ dữ liệu để dự đoán",
        )
    return _serialize_prediction(pred)


class SimulateItem(BaseModel):
    enrollment_id: UUID
    hypothetical_score: float


@router.post("/me/simulate")
async def simulate_prediction(
    items: list[SimulateItem],
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    What-if risk simulation — nhận danh sách điểm giả định cho các môn đang học,
    trả về risk score mô phỏng. Không lưu vào DB.
    """
    if not prediction_service.is_loaded:
        raise HTTPException(status_code=503, detail="AI model chưa load")

    # Fetch enrollments
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
    )
    enrollments = list(result.scalars().all())
    if not enrollments:
        raise HTTPException(status_code=422, detail="Chưa đủ dữ liệu để mô phỏng")

    # Get current risk score from latest prediction (for delta)
    latest_pred = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student.id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    current = latest_pred.scalar_one_or_none()
    original_risk_score = round(current.risk_score, 4) if current else None
    original_risk_level = current.risk_level.value if current else None

    # Build override map {enrollment_id → hypothetical_score}
    override_map = {str(item.enrollment_id): item.hypothetical_score for item in items}

    # Deep-copy enrollments and apply hypothetical scores
    simulated = []
    for e in enrollments:
        if str(e.id) in override_map:
            score = override_map[str(e.id)]
            score = max(0.0, min(10.0, score))
            sim_e = copy.copy(e)
            sim_e.total_score = score
            sim_e.grade_letter = score_to_grade_letter(score)
            sim_e.status = (
                EnrollmentStatus.passed if score >= 4.0 else EnrollmentStatus.failed
            )
            simulated.append(sim_e)
        else:
            simulated.append(e)

    # Extract features from simulated enrollments
    import pandas as pd
    features = await extract_features(student, simulated)
    X = pd.DataFrame([features], columns=FEATURE_NAMES).astype(float)
    raw_proba = float(prediction_service._model.predict_proba(X)[0, 1])
    simulated_score, _, _ = _apply_early_warning_calibration(raw_proba, student, features)
    simulated_score = round(simulated_score, 4)
    simulated_level = risk_score_to_level(simulated_score).value

    delta = round(simulated_score - (original_risk_score or simulated_score), 4)

    return {
        "original_risk_score": original_risk_score,
        "original_risk_level": original_risk_level,
        "simulated_risk_score": simulated_score,
        "simulated_risk_level": simulated_level,
        "delta_risk_score": delta,
    }


@router.post("/batch-run", dependencies=[Depends(require_admin)])
async def run_batch_prediction(db: AsyncSession = Depends(get_db)):
    """[Admin] Trigger batch predict cho tất cả SV (giống cron daily 02:00)."""
    if not prediction_service.is_loaded:
        raise HTTPException(status_code=503, detail="AI model chưa load")
    count = await prediction_service.predict_batch(db, only_synthetic=False)
    return {"message": f"Batch predict thành công cho {count} SV", "count": count}
