"""Pydantic schemas cho admin endpoints (M7)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Dashboard ──────────────────────────────────────────────

class WarningLevelBucket(BaseModel):
    level: int
    count: int


class RiskBucket(BaseModel):
    bucket: Literal["low", "medium", "high", "critical"]
    count: int
    label_vi: str


class FacultyWarningBucket(BaseModel):
    faculty: str
    warning_count: int
    total_students: int
    pct: float


class TopRiskStudent(BaseModel):
    student_id: UUID
    mssv: str
    full_name: str
    faculty: str
    gpa_cumulative: float
    warning_level: int
    risk_score: float | None = None
    risk_level: str | None = None


class AdminDashboardStats(BaseModel):
    total_students: int
    total_warned: int                # warning_level >= 1
    total_high_risk: int             # risk_score >= 0.6
    total_critical: int              # risk_score >= 0.8
    by_warning_level: list[WarningLevelBucket]
    by_risk_level: list[RiskBucket]
    by_faculty: list[FacultyWarningBucket]
    top_risk: list[TopRiskStudent]
    generated_at: datetime


# ─── Students list / detail ─────────────────────────────────

class AdminStudentListItem(BaseModel):
    student_id: UUID
    mssv: str
    full_name: str
    faculty: str
    major: str
    cohort: int
    email: str
    gpa_cumulative: float
    credits_earned: int
    warning_level: int
    risk_score: float | None = None
    risk_level: str | None = None


class AdminStudentListResponse(BaseModel):
    items: list[AdminStudentListItem]
    total: int
    page: int
    size: int


class GpaHistoryPoint(BaseModel):
    semester: str
    semester_gpa: float
    credits_taken: int
    courses_count: int


class AdminWarningSummary(BaseModel):
    id: UUID
    level: int
    semester: str
    reason: str
    gpa_at_warning: float
    is_resolved: bool
    sent_at: datetime | None
    created_by: str


class AdminStudentDetail(BaseModel):
    student_id: UUID
    mssv: str
    full_name: str
    faculty: str
    major: str
    cohort: int
    email: str
    is_active: bool
    gpa_cumulative: float
    credits_earned: int
    warning_level: int
    failed_courses_total: int
    gpa_history: list[GpaHistoryPoint]
    risk_score: float | None
    risk_level: str | None
    risk_factors: list[dict[str, Any]]
    warnings: list[AdminWarningSummary]


# ─── Manual warning ─────────────────────────────────────────

class AdminManualWarningCreate(BaseModel):
    student_id: UUID
    level: int = Field(ge=1, le=3)
    semester: str
    reason: str


# ─── Pending warnings (AI suggestions) ──────────────────────

class PendingWarningItem(BaseModel):
    student_id: UUID
    mssv: str
    full_name: str
    faculty: str
    semester: str
    suggested_level: int
    risk_score: float
    risk_level: str
    reason: str
    gpa_cumulative: float


class PendingWarningsResponse(BaseModel):
    items: list[PendingWarningItem]
    total: int
    threshold: float
    last_batch_at: datetime | None


class ApprovePendingPayload(BaseModel):
    student_id: UUID
    semester: str
    level: int = Field(ge=1, le=3)
    reason: str | None = None


# ─── Import ─────────────────────────────────────────────────

class ImportError(BaseModel):
    row: int
    column: str | None = None
    reason: str
    raw: dict[str, Any] | None = None


class ImportResult(BaseModel):
    type: Literal["students", "grades"]
    filename: str
    total_rows: int
    created: int
    updated: int
    skipped: int
    errors: list[ImportError]
    success: bool


class ImportHistoryItem(BaseModel):
    id: UUID
    type: Literal["students", "grades"]
    filename: str
    total_rows: int
    created: int
    updated: int
    error_count: int
    success: bool
    uploaded_at: datetime
    uploaded_by_email: str | None


# ─── Statistics / reports ───────────────────────────────────

class SemesterWarningCount(BaseModel):
    semester: str
    count: int


class GpaDistributionBucket(BaseModel):
    bucket: str   # "<1.5", "1.5-2.0", ...
    count: int


class RiskDistributionBucket(BaseModel):
    bucket: str
    label_vi: str
    count: int
    pct: float


class WarningLevelReportBucket(BaseModel):
    level: int
    label: str
    count: int
    pct: float


class PassFailBucket(BaseModel):
    status: str
    label: str
    count: int
    pct: float


class AdminStatistics(BaseModel):
    gpa_average: float
    warning_rate_pct: float
    improvement_rate_pct: float | None
    pass_rate_pct: float | None
    total_students: int
    total_warned: int = 0
    total_high_risk: int = 0
    total_critical: int = 0
    by_semester: list[SemesterWarningCount]
    gpa_distribution: list[GpaDistributionBucket]
    by_warning_level: list[WarningLevelReportBucket] = []
    risk_distribution: list[RiskDistributionBucket] = []
    by_faculty: list[FacultyWarningBucket] = []
    latest_pass_fail: list[PassFailBucket] = []
    semester_now: str | None


# ─── Threshold config ───────────────────────────────────────

class ThresholdConfig(BaseModel):
    ai_early_warning_threshold: float
    gpa_safe: float = 2.0
    gpa_warning_l1: float = 1.2
    gpa_warning_l2: float = 1.0
    gpa_dismissal: float = 0.8
    semester_gpa_l1: float = 0.8
