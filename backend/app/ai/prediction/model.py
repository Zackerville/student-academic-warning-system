"""
Prediction service — singleton load model lúc startup, predict + lưu DB.

Usage:
  from app.ai.prediction.model import prediction_service
  result = await prediction_service.predict_for_student(student_id, db)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.prediction.explainer import RiskExplainer
from app.ai.prediction.features import FEATURE_NAMES, FEATURE_VERSION, extract_features
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.prediction import Prediction, RiskLevel
from app.models.student import Student

MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "xgboost_v1.pkl"
METRICS_PATH = MODEL_DIR / "metrics_v1.json"
FEATURES_PATH = MODEL_DIR / "feature_names.json"

# Risk level thresholds — đã chốt với user
RISK_THRESHOLDS = {
    "low":      (0.0,  0.3),
    "medium":   (0.3,  0.5),
    "high":     (0.5,  0.75),
    "critical": (0.75, 1.01),
}


def risk_score_to_level(score: float) -> RiskLevel:
    if score >= 0.75:
        return RiskLevel.critical
    if score >= 0.5:
        return RiskLevel.high
    if score >= 0.3:
        return RiskLevel.medium
    return RiskLevel.low


def _current_semester_code(now: Optional[datetime] = None) -> str:
    """Map ngày hiện tại → semester code YYN."""
    now = now or datetime.now()
    year_short = str(now.year)[2:]
    month = now.month
    # HK1: tháng 9-12 (năm đó), HK2: tháng 1-5 (năm sau), HK3: tháng 6-8
    if month >= 9:
        # HK1 năm học (year)-(year+1)
        return f"{year_short}1"
    if month <= 5:
        # HK2 năm học (year-1)-(year)
        prev = str(now.year - 1)[2:]
        return f"{prev}2"
    # tháng 6-8 → HK3 hè
    prev = str(now.year - 1)[2:]
    return f"{prev}3"


class PredictionService:
    """Singleton load XGBoost model + SHAP explainer."""

    def __init__(self):
        self._model = None
        self._explainer: Optional[RiskExplainer] = None
        self._metrics: Optional[dict] = None
        self._loaded = False

    def load(self) -> bool:
        """Load model từ disk. Return True nếu thành công."""
        if not MODEL_PATH.exists():
            logger.warning(f"Model not found at {MODEL_PATH} — train first")
            return False
        try:
            self._model = joblib.load(MODEL_PATH)
            feature_sets: list[list[str]] = []
            if FEATURES_PATH.exists():
                feature_sets.append(json.loads(FEATURES_PATH.read_text()))
            if hasattr(self._model, "get_booster"):
                booster_features = self._model.get_booster().feature_names
                if booster_features:
                    feature_sets.append(booster_features)

            stale_features = next(
                (features for features in feature_sets if features != FEATURE_NAMES),
                None,
            )
            if stale_features:
                logger.warning(
                    "Prediction model feature set is stale — retrain required. "
                    f"model={stale_features}, code={FEATURE_NAMES}"
                )
                self._model = None
                self._explainer = None
                self._metrics = None
                self._loaded = False
                return False

            self._explainer = RiskExplainer(self._model)
            if METRICS_PATH.exists():
                self._metrics = json.loads(METRICS_PATH.read_text())
            self._loaded = True
            logger.info(f"Prediction model loaded from {MODEL_PATH}")
            return True
        except Exception as exc:
            logger.error(f"Failed to load prediction model: {exc}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def threshold(self) -> float:
        """Decision threshold (from training metrics)."""
        if self._metrics:
            return float(self._metrics.get("decision_threshold", 0.5))
        return 0.5

    async def predict_for_student(
        self,
        student: Student,
        db: AsyncSession,
        save: bool = True,
    ) -> Optional[Prediction]:
        """
        Predict risk cho 1 SV. Lưu vào bảng predictions nếu save=True.
        Trả về Prediction record (đã commit) hoặc None nếu chưa đủ data.
        Tự động sync stats trước để đảm bảo gpa_cumulative + warning_level mới nhất.
        """
        if not self._loaded or self._model is None or self._explainer is None:
            return None

        # Sync stats để student.gpa_cumulative + credits_earned + warning_level fresh
        # (tránh dùng giá trị stale khi SV vừa import myBK xong)
        from app.api.v1.students import _sync_student_stats
        await _sync_student_stats(student, db)
        await db.refresh(student)

        # Fetch enrollments
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.student_id == student.id)
            .options(selectinload(Enrollment.course))
        )
        enrollments = result.scalars().all()
        if not enrollments:
            # Cold start — không đủ data
            return None

        # Extract features
        features = await extract_features(student, enrollments)

        # Predict (probability)
        import pandas as pd
        X = pd.DataFrame([features], columns=FEATURE_NAMES).astype(float)
        proba = float(self._model.predict_proba(X)[0, 1])

        # Explain
        factors = self._explainer.explain(features, top_k=5)

        # Course-level prediction (heuristic)
        predicted_courses = self._predict_courses(enrollments, proba)

        risk_level = risk_score_to_level(proba)
        semester = _current_semester_code()

        prediction = Prediction(
            student_id=student.id,
            semester=semester,
            risk_score=proba,
            risk_level=risk_level,
            risk_factors={
                "feature_version": FEATURE_VERSION,
                "factors": factors,
                "features": features,
            },
            predicted_courses=predicted_courses,
        )

        if save:
            db.add(prediction)
            await db.commit()
            await db.refresh(prediction)

        return prediction

    def _predict_courses(
        self,
        enrollments: list[Enrollment],
        student_risk: float,
    ) -> list[dict]:
        """
        Heuristic predict pass/fail từng môn HK hiện tại.
        Course difficulty = lịch sử fail rate của môn từ enrollments có sẵn.
        Pass prob = 1 - (student_risk * difficulty * 1.2)
        """
        # Fetch latest semester
        if not enrollments:
            return []
        latest_sem = max(e.semester for e in enrollments)

        # Course-level fail rate from enrollments của HK hiện tại của SV
        current_sems = [e for e in enrollments if e.semester == latest_sem]

        # Stats per course từ all SV (need DB query) — simplify: dùng global avg
        # Cho M4 simple: pass_prob phụ thuộc vào student_risk + môn cụ thể
        results = []
        for e in current_sems:
            if e.status != EnrollmentStatus.enrolled:
                continue  # Đã pass/fail rồi, không cần predict
            # Heuristic: pass_prob = (1 - student_risk * 1.1) clamp [0.05, 0.95]
            base_pass = 1.0 - student_risk * 1.1
            # Adjust theo current grades nếu có
            if e.midterm_score is not None:
                # Nếu đã có midterm và pass thì cao hơn, fail thì thấp hơn
                midterm_factor = (e.midterm_score - 5.0) / 10.0  # -0.5 to +0.5
                base_pass += midterm_factor * 0.3
            pass_prob = max(0.05, min(0.95, base_pass))
            results.append({
                "course_id": str(e.course_id),
                "course_code": e.course.course_code,
                "course_name": e.course.name,
                "credits": e.course.credits,
                "pass_probability": round(pass_prob, 3),
            })
        return results

    async def predict_batch(self, db: AsyncSession, only_synthetic: bool = False) -> int:
        """
        Predict cho mọi SV (or synthetic only). Trả số SV đã predict.
        """
        if not self._loaded:
            return 0

        q = select(Student)
        if only_synthetic:
            q = q.where(Student.mssv.like("SYN%"))
        result = await db.execute(q)
        students = result.scalars().all()

        count = 0
        for student in students:
            try:
                pred = await self.predict_for_student(student, db, save=True)
                if pred:
                    count += 1
            except Exception as exc:
                logger.error(f"Predict failed for {student.mssv}: {exc}")
        return count


# Singleton instance
prediction_service = PredictionService()
