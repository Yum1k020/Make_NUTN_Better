from __future__ import annotations

from datetime import date as Date, datetime
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.scheduler import build_study_plan


class AllowedWindow(BaseModel):
    date: Date | None = None
    weekday: int | None = Field(default=None, ge=1, le=7)
    start_time: str
    end_time: str

    @model_validator(mode="after")
    def require_date_or_weekday(self):
        if self.date is None and self.weekday is None:
            raise ValueError("either date or weekday is required")
        return self


class BusyInterval(BaseModel):
    source_type: str
    source_id: str
    title: str
    starts_at: datetime
    ends_at: datetime


class StudyPlanRequest(BaseModel):
    plan_id: str = Field(min_length=1)
    start_date: Date
    exam_date: Date
    target_minutes: int = Field(gt=0)
    session_minutes: int = Field(gt=0)
    allowed_windows: List[AllowedWindow]
    busy_intervals: List[BusyInterval] = []

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_date >= self.exam_date:
            raise ValueError("start_date must be earlier than exam_date")
        return self


class StudySession(BaseModel):
    plan_id: str
    starts_at: datetime
    ends_at: datetime
    minutes: int


class StudyPlanResponse(BaseModel):
    plan_id: str
    suggested_sessions: List[StudySession]
    scheduled_minutes: int
    remaining_minutes: int
    reason: str


app = FastAPI(title="Make_NUTN_Better Week 02 Baseline", version="0.2.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/study-plan", response_model=StudyPlanResponse)
def study_plan(request: StudyPlanRequest):
    try:
        return build_study_plan(
            plan_id=request.plan_id,
            start_date=request.start_date,
            exam_date=request.exam_date,
            target_minutes=request.target_minutes,
            session_minutes=request.session_minutes,
            allowed_windows=[item.model_dump(exclude_none=True, mode="json") for item in request.allowed_windows],
            busy_intervals=[item.model_dump(mode="json") for item in request.busy_intervals],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "UPSTREAM_GENERATION_UNAVAILABLE", "message": str(exc)},
        ) from exc
