"""Pydantic schemas for the M9 schedule feature (TKB + Exam + Personal Events)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Timetable ─────────────────────────────────────────────

class TimetableSessionOut(BaseModel):
    course_code: str
    course_name: str
    credits: int
    group: str
    day_of_week: Optional[int] = None
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room: str
    campus: str
    active_weeks: list[int] = Field(default_factory=list)


class TimetableResponse(BaseModel):
    semester: str
    sessions: list[TimetableSessionOut]
    week_1_monday: Optional[str] = None  # ISO date — anchors academic week 1
    updated_at: Optional[datetime] = None


class TimetableImportRequest(BaseModel):
    paste_text: str = Field(..., min_length=20)
    merge: bool = False  # True → gộp vào TKB hiện có thay vì xoá trắng


class TimetableImportResponse(BaseModel):
    semester: str
    sessions_count: int
    enrollments_created: int
    enrollments_skipped: int
    timetable: TimetableResponse


# ─── Exam schedule ─────────────────────────────────────────

class ExamEntryOut(BaseModel):
    course_code: str
    course_name: str
    group: str
    exam_date: str
    exam_type: str  # "CK" | "GK"
    campus: str
    room: str
    day_of_week: Optional[int] = None
    start_time: str
    duration_min: int


class ExamScheduleResponse(BaseModel):
    semester: str
    exams: list[ExamEntryOut]
    updated_at: Optional[datetime] = None


class ExamScheduleImportRequest(BaseModel):
    paste_text: str = Field(..., min_length=20)


class ExamScheduleImportResponse(BaseModel):
    semester: str
    exams_count: int
    exam_schedule: ExamScheduleResponse


# ─── Personal events ───────────────────────────────────────

class PersonalEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    color: Optional[str] = Field(default=None, max_length=20)  # e.g. "purple", "#7c3aed"


class PersonalEventOut(BaseModel):
    id: uuid.UUID
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    color: Optional[str] = None
    created_at: datetime


class PersonalEventListResponse(BaseModel):
    items: list[PersonalEventOut]
