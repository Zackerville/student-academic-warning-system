"""
SHAP Explainer — chuyển feature importance thành lý do tiếng Việt.

Output cho mỗi prediction: top-5 risk_factors dạng:
  [
    {"feature": "gpa_cumulative_deficit", "label": "GPA tích lũy khoảng 0.98 (< 2.0)", "impact": 0.32, "direction": "+"},
    {"feature": "unresolved_failed_courses", "label": "Còn 3 môn chưa qua", "impact": 0.21, "direction": "+"},
    ...
  ]
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from xgboost import XGBClassifier

from app.ai.prediction.features import ATTENDANCE_SAFE_MIN, FEATURE_NAMES, GPA_SAFE_TARGET


def _format_value(feature: str, value: float) -> str:
    """Format giá trị feature đẹp cho hiển thị."""
    if feature == "gpa_cumulative_deficit":
        if value <= 0:
            return f"GPA tích lũy đang trên mốc an toàn {GPA_SAFE_TARGET:.1f}"
        approx_gpa = max(0.0, GPA_SAFE_TARGET - value)
        return f"GPA tích lũy khoảng {approx_gpa:.2f}, dưới mốc an toàn"
    if feature == "gpa_recent_deficit":
        if value <= 0:
            return f"GPA học kỳ gần nhất đang trên mốc an toàn {GPA_SAFE_TARGET:.1f}"
        approx_gpa = max(0.0, GPA_SAFE_TARGET - value)
        return f"GPA học kỳ gần nhất khoảng {approx_gpa:.2f}, dưới mốc an toàn"
    if feature == "gpa_trend_drop":
        if value <= 0:
            return "GPA gần đây không có xu hướng giảm"
        return f"GPA đang giảm khoảng {value:.2f} điểm mỗi học kỳ"
    if feature == "low_gpa_streak":
        if value <= 0:
            return "Không có chuỗi học kỳ GPA dưới 2.0"
        return f"{int(value)} học kỳ liên tiếp GPA dưới 2.0"
    if feature == "unresolved_failed_courses":
        if value <= 0:
            return "Không còn môn có tín chỉ nào chưa đạt"
        return f"Còn {int(value)} môn có tín chỉ chưa đạt"
    if feature == "unresolved_failed_last_semester":
        if value <= 0:
            return "Học kỳ gần nhất không còn môn F có tín chỉ chưa xử lý"
        return f"Còn {int(value)} môn F có tín chỉ từ học kỳ gần nhất"
    if feature == "unresolved_failed_retake_count":
        if value <= 0:
            return "Không có môn học lại vẫn chưa đạt"
        return f"Có {int(value)} môn học lại nhưng vẫn chưa đạt"
    if feature == "withdrawn_count":
        if value <= 0:
            return "Không có môn có tín chỉ bị rút"
        return f"Đã rút {int(value)} môn có tín chỉ"
    if feature == "pass_rate_deficit":
        pass_rate = max(0.0, min(1.0, 1.0 - value))
        return f"Tỉ lệ qua môn có tín chỉ khoảng {pass_rate * 100:.0f}%"
    if feature == "attendance_risk":
        if value <= 0:
            return "Không có dấu hiệu điểm danh thấp"
        approx_attendance = ATTENDANCE_SAFE_MIN * (1.0 - value)
        return f"Điểm danh trung bình khoảng {approx_attendance:.0f}%, dưới ngưỡng an toàn"
    if feature == "recovered_failed_courses":
        if value <= 0:
            return "Chưa có môn F có tín chỉ nào được học lại đạt"
        return f"Đã học lại/cải thiện thành công {int(value)} môn từng F"
    return "Một tín hiệu học vụ khác ảnh hưởng đến dự đoán"


def _should_skip_factor(feature: str, value: float, shap_val: float) -> bool:
    """Ẩn các reason đúng về toán nhưng khó hiểu/không hành động được."""
    is_protective_feature = feature == "recovered_failed_courses"
    is_risk_feature = feature in {
        "gpa_cumulative_deficit",
        "gpa_recent_deficit",
        "gpa_trend_drop",
        "low_gpa_streak",
        "unresolved_failed_courses",
        "unresolved_failed_last_semester",
        "unresolved_failed_retake_count",
        "withdrawn_count",
        "pass_rate_deficit",
        "attendance_risk",
    }

    # Protective feature chỉ nên hiện khi nó thật sự kéo risk xuống.
    if is_protective_feature:
        return value <= 0 or shap_val > 0

    # Risk feature bằng 0 chỉ có ý nghĩa khi nó kéo risk xuống
    # (vd "Không còn môn nào chưa qua" giảm rủi ro).
    if is_risk_feature and value <= 0 and shap_val > 0:
        return True

    # Risk feature > 0 nhưng SHAP âm là so-sánh-với-baseline, dễ tạo câu
    # ngược đời kiểu "7 HK GPA thấp làm giảm rủi ro"; ẩn khỏi top reasons.
    if is_risk_feature and value > 0 and shap_val < 0:
        return True

    return False


def _format_impact(direction: str, abs_impact: float) -> str:
    """Format mức độ đóng góp."""
    pct = abs_impact * 100
    sign = "+" if direction == "+" else "−"
    return f"{sign}{pct:.0f}%"


class RiskExplainer:
    """SHAP-based explainer cho XGBoost classifier."""

    def __init__(self, model: XGBClassifier):
        self.model = model
        self.explainer = shap.TreeExplainer(model)

    def explain(
        self,
        features: dict[str, float],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Trả top-k factors theo |SHAP value| giảm dần.
        Direction "+" = tăng risk, "−" = giảm risk.
        Impact normalize sao cho tổng |impact| top-k = 100%.
        """
        X = pd.DataFrame([features], columns=FEATURE_NAMES).astype(float)
        shap_values = self.explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        values = shap_values[0]

        # Sort by absolute SHAP value
        sorted_idx = np.argsort(-np.abs(values))

        # Pick top-k với label hợp lệ
        picked: list[tuple[int, float, str]] = []
        for idx in sorted_idx:
            if len(picked) >= top_k:
                break
            feature = FEATURE_NAMES[idx]
            shap_val = float(values[idx])
            raw_value = float(features[feature])
            label = _format_value(feature, raw_value)
            if label is None:
                continue
            if _should_skip_factor(feature, raw_value, shap_val):
                continue
            if abs(shap_val) < 0.01:
                continue
            picked.append((idx, shap_val, label))

        # Normalize impact: sum |shap| of top-k = 100%
        total_abs = sum(abs(s) for _, s, _ in picked)
        if total_abs == 0:
            total_abs = 1.0

        factors: list[dict] = []
        for idx, shap_val, label in picked:
            feature = FEATURE_NAMES[idx]
            raw_value = float(features[feature])
            normalized = abs(shap_val) / total_abs
            direction = "+" if shap_val > 0 else "−"
            factors.append({
                "feature": feature,
                "label": label,
                "impact": normalized,
                "impact_str": _format_impact(direction, normalized),
                "direction": direction,
                "shap_value": shap_val,
                "raw_value": raw_value,
            })

        return factors

    def get_global_importance(self) -> list[dict]:
        """Trả feature importance global từ XGBoost (không cần data)."""
        importances = self.model.feature_importances_
        ranked = sorted(
            zip(FEATURE_NAMES, importances),
            key=lambda x: -x[1],
        )
        return [
            {"feature": name, "importance": float(score)}
            for name, score in ranked
            if score > 0
        ]
