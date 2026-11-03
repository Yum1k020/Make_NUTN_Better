"""Shared provider contract for the study-planning agent loop."""

from __future__ import annotations

from typing import Any


TOOL_NAME = "get_validated_study_plan"


class StudyAgentProviderError(RuntimeError):
    """Safe provider failure that never includes credentials or raw payloads."""

    def __init__(self, code: str, *, attempted: bool = False):
        super().__init__(code)
        self.code = code
        self.attempted = attempted


def tool_declaration() -> dict[str, Any]:
    """Return the strict, provider-neutral study-plan tool schema."""

    event = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "date": {"type": "string"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "location": {"type": "string"},
        },
        "required": ["id", "title", "date", "start", "end", "location"],
        "additionalProperties": False,
    }
    return {
        "name": TOOL_NAME,
        "description": (
            "依課表、私人行程與考試需求，取得由確定性規則引擎計算並驗證的複習計畫。"
            "這是唯讀預覽，不會建立或修改資料。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "startDate": {"type": "string"},
                "examDate": {"type": "string"},
                "hours": {"type": "number"},
                "sessionHours": {"type": "number"},
                "allowedPeriods": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening"],
                    },
                },
                "courseName": {"type": "string"},
                "personalEvents": {"type": "array", "items": event},
            },
            "required": [
                "startDate",
                "examDate",
                "hours",
                "sessionHours",
                "allowedPeriods",
                "courseName",
                "personalEvents",
            ],
            "additionalProperties": False,
        },
    }
