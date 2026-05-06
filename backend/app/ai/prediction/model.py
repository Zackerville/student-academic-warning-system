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
from app.services.grade_aggregator import sync_student_stats

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


def _risk_factor(
    feature: str,
    label: str,
    impact: float,
    raw_value: float,
) -> dict:
    """Build a deterministic early-warning factor for the UI."""
    impact = max(0.01, min(1.0, impact))
    return {
        "feature": feature,
        "label": label,
        "impact": impact,
        "impact_str": f"+{impact * 100:.0f}%",
        "direction": "+",
        "shap_value": 0.0,
        "raw_value": raw_value,
    }


def _early_warning_rules(student: Student, features: dict[str, float]) -> list[tuple[float, dict]]:
    """
    Product calibration for early warning.

    The XGBoost model is trained to predict formal warning risk from synthetic
    labels. This layer makes the displayed risk match the product expectation:
    average GPA -> medium watch zone, low GPA -> high, formal-warning GPA -> critical.
    """
    gpa = float(student.gpa_cumulative or 0.0)
    warning_level = int(student.warning_level or 0)
    unresolved = int(features.get("unresolved_failed_courses", 0.0))
    unresolved_retake = int(features.get("unresolved_failed_retake_count", 0.0))
    recovered = int(features.get("recovered_failed_courses", 0.0))
    low_streak = int(features.get("low_gpa_streak", 0.0))
    pass_rate = 1.0 - float(features.get("pass_rate_deficit", 0.0))
    recent_deficit = float(features.get("gpa_recent_deficit", 0.0))
    recent_gpa = max(0.0, 2.0 - recent_deficit) if recent_deficit > 0 else None

    rules: list[tuple[float, dict]] = []

    formal_warning_is_current = (
        warning_level >= 1
        and (
            gpa < 2.0
            or unresolved > 0
            or unresolved_retake > 0
            or low_streak > 0
            or recent_gpa is not None
            or pass_rate < 0.85
        )
    )

    if formal_warning_is_current or gpa < 1.2:
        rules.append((
            0.78,
            _risk_factor(
                "early_warning.formal_threshold",
                f"GPA tích lũy {gpa:.2f} đã chạm vùng cảnh báo học vụ",
                0.55,
                gpa,
            ),
        ))
    elif gpa < 1.6:
        rules.append((
            0.62,
            _risk_factor(
                "early_warning.very_low_gpa",
                f"GPA tích lũy {gpa:.2f} rất gần ngưỡng cảnh báo",
                0.45,
                gpa,
            ),
        ))
    elif gpa < 2.0:
        rules.append((
            0.52,
            _risk_factor(
                "early_warning.low_gpa",
                f"GPA tích lũy {gpa:.2f} dưới mốc an toàn 2.0",
                0.38,
                gpa,
            ),
        ))
    elif gpa < 2.5:
        rules.append((
            0.34,
            _risk_factor(
                "early_warning.mid_low_gpa",
                f"GPA tích lũy {gpa:.2f} ở vùng trung bình-thấp",
                0.26,
                gpa,
            ),
        ))
    elif gpa < 3.0 and (unresolved > 0 or recovered >= 3 or low_streak > 0):
        rules.append((
            0.30,
            _risk_factor(
                "early_warning.average_gpa_with_history",
                f"GPA tích lũy {gpa:.2f} chưa cao và có lịch sử học vụ cần theo dõi",
                0.22,
                gpa,
            ),
        ))

    if unresolved >= 3:
        rules.append((
            0.55,
            _risk_factor(
                "early_warning.unresolved_failed_courses",
                f"Còn {unresolved} môn chưa đạt",
                0.38,
                float(unresolved),
            ),
        ))
    elif unresolved == 2:
        rules.append((
            0.45,
            _risk_factor(
                "early_warning.unresolved_failed_courses",
                "Còn 2 môn chưa đạt",
                0.30,
                2.0,
            ),
        ))
    elif unresolved == 1:
        rules.append((
            0.34,
            _risk_factor(
                "early_warning.unresolved_failed_courses",
                "Còn 1 môn chưa đạt",
                0.24,
                1.0,
            ),
        ))

    if unresolved_retake > 0:
        rules.append((
            0.50,
            _risk_factor(
                "early_warning.unresolved_failed_retake",
                f"Có {unresolved_retake} môn học lại nhưng vẫn chưa qua",
                0.34,
                float(unresolved_retake),
            ),
        ))

    if low_streak >= 2:
        rules.append((
            0.45,
            _risk_factor(
                "early_warning.low_gpa_streak",
                f"{low_streak} học kỳ liên tiếp GPA dưới 2.0",
                0.30,
                float(low_streak),
            ),
        ))
    elif low_streak == 1:
        rules.append((
            0.32,
            _risk_factor(
                "early_warning.low_gpa_streak",
                "HK gần nhất GPA dưới 2.0",
                0.20,
                1.0,
            ),
        ))

    if recent_gpa is not None and recent_gpa < 1.6:
        rules.append((
            0.50,
            _risk_factor(
                "early_warning.recent_low_gpa",
                f"GPA học kỳ gần nhất khoảng {recent_gpa:.2f}",
                0.32,
                recent_gpa,
            ),
        ))
    elif recent_gpa is not None and recent_gpa < 2.0:
        rules.append((
            0.35,
            _risk_factor(
                "early_warning.recent_low_gpa",
                f"GPA học kỳ gần nhất khoảng {recent_gpa:.2f} dưới mốc an toàn",
                0.22,
                recent_gpa,
            ),
        ))

    if pass_rate < 0.85:
        rules.append((
            0.42,
            _risk_factor(
                "early_warning.low_pass_rate",
                f"Tỉ lệ pass chỉ khoảng {pass_rate * 100:.0f}%",
                0.28,
                pass_rate,
            ),
        ))
    elif pass_rate < 0.95 and gpa < 2.8:
        rules.append((
            0.32,
            _risk_factor(
                "early_warning.pass_rate_watch",
                f"Tỉ lệ pass khoảng {pass_rate * 100:.0f}%, cần theo dõi",
                0.18,
                pass_rate,
            ),
        ))

    if recovered >= 5 and gpa < 3.0:
        rules.append((
            0.36,
            _risk_factor(
                "early_warning.recovered_failed_history",
                f"Từng có {recovered} môn F đã học lại/cải thiện",
                0.24,
                float(recovered),
            ),
        ))
    elif recovered >= 3 and gpa < 3.0:
        rules.append((
            0.32,
            _risk_factor(
                "early_warning.recovered_failed_history",
                f"Từng có {recovered} môn F đã học lại/cải thiện",
                0.18,
                float(recovered),
            ),
        ))

    return rules


def _apply_early_warning_calibration(
    raw_score: float,
    student: Student,
    features: dict[str, float],
) -> tuple[float, list[dict], float]:
    """Return calibrated score, explanatory rule factors, and applied floor."""
    rules = _early_warning_rules(student, features)
    if not rules:
        return raw_score, [], 0.0

    floor = max(score for score, _ in rules)
    calibrated = max(raw_score, floor)
    rule_factors = [
        factor
        for _, factor in sorted(rules, key=lambda item: item[0], reverse=True)
    ][:3]
    return calibrated, rule_factors, floor


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

        # Sync cảnh báo trước để tránh dùng warning_level cũ từ cold-start GPA 0.0.
        from app.services import warning_engine

        await warning_engine.sync_current_warning_level(db, student)

        # Sync stats để student.gpa_cumulative + credits_earned fresh
        # (tránh dùng giá trị stale khi SV vừa import myBK xong)
        await sync_student_stats(student, db)
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
        raw_proba = float(self._model.predict_proba(X)[0, 1])
        proba, calibration_factors, calibration_floor = _apply_early_warning_calibration(
            raw_proba,
            student,
            features,
        )

        # Explain
        shap_factors = self._explainer.explain(features, top_k=5)
        factors = (calibration_factors + shap_factors)[:5]

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
                "raw_model_score": raw_proba,
                "calibrated_score": proba,
                "calibration_floor": calibration_floor,
                "calibration_applied": proba > raw_proba,
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
