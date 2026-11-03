"""Backend Gemini/ADC tool loop for the main study-planning demo."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Callable

from flask import current_app, jsonify, request
from flask_smorest import Blueprint

from .study_agent_vertex import TOOL_NAME, VertexGeminiADCClient, VertexProviderError


routes = Blueprint(
    "study-agent",
    __name__,
    url_prefix="/api/v1/study-agent",
    description="使用 Google Cloud ADC 呼叫 Gemini 的唯讀學習規劃工具流程",
)

PERIODS = {
    "morning": (8 * 60, 12 * 60),
    "afternoon": (13 * 60, 18 * 60),
    "evening": (18 * 60, 22 * 60),
}
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
REQUEST_FIELDS = {
    "startDate",
    "examDate",
    "hours",
    "sessionHours",
    "allowedPeriods",
    "courseName",
    "personalEvents",
}
EVENT_REQUIRED_FIELDS = {"id", "title", "date", "start", "end"}
EVENT_ALLOWED_FIELDS = EVENT_REQUIRED_FIELDS | {"location"}
SOURCE_IDS = {
    "planner-rule",
    "weekly-classes-fixture",
    "tasks-events-local",
}

WEEKLY_CLASSES = [
    {"weekday": 1, "start": "09:00", "end": "10:50", "title": "微積分（一）"},
    {"weekday": 1, "start": "14:00", "end": "15:50", "title": "專題討論"},
    {"weekday": 2, "start": "09:00", "end": "10:50", "title": "英文閱讀與寫作"},
    {"weekday": 2, "start": "11:00", "end": "12:50", "title": "程式設計（一）"},
    {"weekday": 4, "start": "09:00", "end": "10:50", "title": "資料結構"},
    {"weekday": 4, "start": "11:00", "end": "12:50", "title": "普通心理學"},
    {"weekday": 4, "start": "14:00", "end": "15:50", "title": "程式設計（一）"},
    {"weekday": 5, "start": "09:00", "end": "10:50", "title": "微積分（一）"},
    {"weekday": 5, "start": "11:00", "end": "12:50", "title": "普通心理學"},
]


class StudyAgentError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        *,
        workflow: dict[str, Any] | None = None,
        issues: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.workflow = workflow
        self.issues = issues or []


def _iso_date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 必須是 YYYY-MM-DD 日期字串。")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"{field} 必須是 YYYY-MM-DD。")
    return value


def _number(value: Any, minimum: float, maximum: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必須是數字。")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} 超出允許範圍。")
    return number


def normalize_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Request body 必須是 JSON object。")
    if set(payload) != REQUEST_FIELDS:
        raise ValueError("Request body 欄位不完整或包含未允許欄位。")
    start_date = _iso_date(payload["startDate"], "startDate")
    exam_date = _iso_date(payload["examDate"], "examDate")
    if exam_date <= start_date:
        raise ValueError("考試日期必須晚於規劃起始日。")
    hours = _number(payload["hours"], 0.5, 100, "hours")
    session_hours = _number(payload["sessionHours"], 0.5, 4, "sessionHours")
    periods = payload["allowedPeriods"]
    if (
        not isinstance(periods, list)
        or not periods
        or len(periods) != len(set(periods))
        or any(period not in PERIODS for period in periods)
    ):
        raise ValueError("allowedPeriods 必須是未重複的合法時段陣列。")
    course_name = payload["courseName"]
    if not isinstance(course_name, str) or not course_name.strip() or len(course_name) > 120:
        raise ValueError("courseName 必須是 1 至 120 字元。")
    events = payload["personalEvents"]
    if not isinstance(events, list) or len(events) > 200:
        raise ValueError("personalEvents 必須是最多 200 筆的陣列。")
    normalized_events = []
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            raise ValueError(f"personalEvents[{index}] 必須是 object。")
        if not EVENT_REQUIRED_FIELDS <= set(item) <= EVENT_ALLOWED_FIELDS:
            raise ValueError(f"personalEvents[{index}] 欄位不合法。")
        for field in ("id", "title"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"personalEvents[{index}].{field} 不可為空。")
        event_date = _iso_date(item["date"], f"personalEvents[{index}].date")
        start, end = item["start"], item["end"]
        if not isinstance(start, str) or not TIME_RE.fullmatch(start):
            raise ValueError(f"personalEvents[{index}].start 格式錯誤。")
        if not isinstance(end, str) or not TIME_RE.fullmatch(end) or end <= start:
            raise ValueError(f"personalEvents[{index}].end 必須晚於 start。")
        location = item.get("location", "")
        if not isinstance(location, str) or len(location) > 200:
            raise ValueError(f"personalEvents[{index}].location 不合法。")
        normalized_events.append(
            {
                "id": item["id"],
                "title": item["title"],
                "date": event_date,
                "start": start,
                "end": end,
                "location": location,
            }
        )
    return {
        "startDate": start_date,
        "examDate": exam_date,
        "hours": int(hours) if hours.is_integer() else hours,
        "sessionHours": int(session_hours) if session_hours.is_integer() else session_hours,
        "allowedPeriods": list(periods),
        "courseName": course_name.strip(),
        "personalEvents": normalized_events,
    }


def _minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def _time(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["date"] == right["date"]
        and _minutes(left["start"]) < _minutes(right["end"])
        and _minutes(right["start"]) < _minutes(left["end"])
    )


def _dates(start: str, end: str) -> list[str]:
    current, final = date.fromisoformat(start), date.fromisoformat(end)
    result = []
    while current < final and len(result) < 60:
        result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def _occupied_on(
    day: str,
    personal_events: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parsed = date.fromisoformat(day)
    javascript_weekday = (parsed.weekday() + 1) % 7
    classes = [
        {**item, "date": day}
        for item in WEEKLY_CLASSES
        if item["weekday"] == javascript_weekday
    ]
    return [
        *classes,
        *(item for item in personal_events if item["date"] == day),
        *(item for item in sessions if item["date"] == day),
    ]


def get_validated_study_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Deterministic read-only tool matching the existing React planner."""

    data = normalize_request(payload)
    target = round(data["hours"] * 60)
    usual = round(data["sessionHours"] * 60)
    sessions: list[dict[str, Any]] = []
    remaining = target
    found_slot = True
    days = _dates(data["startDate"], data["examDate"])
    while remaining > 0 and found_slot:
        found_slot = False
        for day in days:
            if remaining <= 0:
                break
            duration = min(usual, remaining)
            occupied = _occupied_on(day, data["personalEvents"], sessions)
            selected = None
            for period in data["allowedPeriods"]:
                lower, upper = PERIODS[period]
                for start in range(lower, upper - duration + 1, 30):
                    candidate = {
                        "date": day,
                        "start": _time(start),
                        "end": _time(start + duration),
                    }
                    if all(not _overlaps(candidate, event) for event in occupied):
                        selected = candidate
                        break
                if selected:
                    break
            if selected:
                sessions.append(
                    {
                        **selected,
                        "id": f"study-{day}-{selected['start']}",
                        "title": f"{data['courseName']}複習",
                        "location": "自行安排",
                        "tone": "amber",
                    }
                )
                remaining -= duration
                found_slot = True
    result = {
        "sessions": sessions,
        "scheduledMinutes": target - remaining,
        "remainingMinutes": remaining,
    }
    issues = verify_plan(data, result)
    if issues:
        raise ValueError("；".join(issues))
    return result


def verify_plan(request_data: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    issues = []
    sessions = plan.get("sessions") if isinstance(plan, dict) else None
    if not isinstance(sessions, list):
        return ["排程結果缺少 sessions。"]
    total = 0
    ids = set()
    accepted: list[dict[str, Any]] = []
    for item in sessions:
        if not isinstance(item, dict) or not {
            "id",
            "date",
            "start",
            "end",
        } <= set(item):
            issues.append("複習時段缺少必要欄位。")
            continue
        if item["id"] in ids:
            issues.append("複習時段 ID 重複。")
        ids.add(item["id"])
        if not request_data["startDate"] <= item["date"] < request_data["examDate"]:
            issues.append("複習時段超出日期範圍。")
        duration = _minutes(item["end"]) - _minutes(item["start"])
        if duration <= 0:
            issues.append("複習時段長度錯誤。")
            continue
        allowed = any(
            _minutes(item["start"]) >= PERIODS[period][0]
            and _minutes(item["end"]) <= PERIODS[period][1]
            for period in request_data["allowedPeriods"]
        )
        if not allowed:
            issues.append("複習時段不在允許範圍。")
        occupied = _occupied_on(item["date"], request_data["personalEvents"], accepted)
        if any(_overlaps(item, event) for event in occupied):
            issues.append("複習時段與既有行程重疊。")
        total += duration
        accepted.append(item)
    target = round(request_data["hours"] * 60)
    if plan.get("scheduledMinutes") != total:
        issues.append("scheduledMinutes 與時段加總不一致。")
    if total + plan.get("remainingMinutes", -1) != target:
        issues.append("已安排與尚缺分鐘數不等於目標。")
    return issues


def _validate_explanation(value: Any, remaining: int) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "summary",
        "warnings",
        "citations",
        "refused",
    }:
        raise ValueError("Gemini structured output 欄位不完整。")
    summary = value["summary"]
    warnings = value["warnings"]
    citations = value["citations"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 600:
        raise ValueError("Gemini summary 不合法。")
    if (
        not isinstance(warnings, list)
        or len(warnings) > 3
        or any(not isinstance(item, str) or not item.strip() for item in warnings)
    ):
        raise ValueError("Gemini warnings 不合法。")
    if (
        not isinstance(citations, list)
        or not citations
        or any(item not in SOURCE_IDS for item in citations)
    ):
        raise ValueError("Gemini citations 不合法。")
    if value["refused"] is not False:
        raise ValueError("Gemini 拒絕已驗證的唯讀排程。")
    if remaining == 0:
        warnings = []
    elif not warnings:
        warnings = [f"尚缺 {remaining} 分鐘，請增加可安排時段。"]
    return {
        "summary": summary.strip(),
        "warnings": warnings,
        "citations": citations,
        "refused": False,
    }


def _stage(identifier: str, label: str, status: str, **evidence: Any) -> dict[str, Any]:
    return {"id": identifier, "label": label, "status": status, "evidence": evidence}


class StudyAgentService:
    def __init__(
        self,
        *,
        provider_factory: Callable[[], Any] = VertexGeminiADCClient,
        tool: Callable[[dict[str, Any]], dict[str, Any]] = get_validated_study_plan,
    ) -> None:
        self.provider_factory = provider_factory
        self.tool = tool

    def run(self, payload: Any) -> dict[str, Any]:
        workflow = {
            "name": "study-plan-gemini-function-calling",
            "version": "midterm-v1",
            "status": "running",
            "stopReason": None,
            "stages": [],
        }
        try:
            normalized = normalize_request(payload)
        except (ValueError, TypeError) as error:
            workflow["stages"].append(
                _stage("validate-request", "需求驗證", "rejected", downstreamCalls=0)
            )
            workflow.update(status="stopped", stopReason="INVALID_REQUEST")
            raise StudyAgentError(
                "INVALID_REQUEST",
                str(error),
                422,
                workflow=workflow,
            ) from error
        workflow["stages"].append(
            _stage(
                "validate-request",
                "需求驗證",
                "completed",
                fieldCount=len(normalized),
                personalEventCount=len(normalized["personalEvents"]),
            )
        )

        provider = self.provider_factory()
        function_call, history, selection_meta = provider.choose_tool(normalized)
        if function_call.get("name") != TOOL_NAME:
            workflow["stages"].append(
                _stage("model-tool-call", "Gemini 工具選擇", "rejected", toolCalls=1)
            )
            workflow.update(status="stopped", stopReason="UNEXPECTED_TOOL")
            raise StudyAgentError(
                "UNEXPECTED_TOOL",
                "Gemini 選擇了未允許的工具。",
                502,
                workflow=workflow,
            )
        workflow["stages"].append(
            _stage(
                "model-tool-call",
                "Gemini 工具選擇",
                "completed",
                tool=TOOL_NAME,
                provider="Google Cloud Vertex AI",
                authentication="ADC",
                model=provider.config.model,
            )
        )
        try:
            model_args = normalize_request(function_call.get("args"))
        except (ValueError, TypeError) as error:
            workflow["stages"].append(
                _stage("validate-tool-args", "工具參數驗證", "rejected", toolCalls=0)
            )
            workflow.update(status="stopped", stopReason="INVALID_TOOL_ARGUMENTS")
            raise StudyAgentError(
                "INVALID_TOOL_ARGUMENTS",
                str(error),
                422,
                workflow=workflow,
            ) from error
        if model_args != normalized:
            workflow["stages"].append(
                _stage("validate-tool-args", "工具參數驗證", "rejected", toolCalls=0)
            )
            workflow.update(status="stopped", stopReason="TOOL_ARGUMENT_MISMATCH")
            raise StudyAgentError(
                "TOOL_ARGUMENT_MISMATCH",
                "Gemini 工具參數與使用者已驗證需求不一致。",
                409,
                workflow=workflow,
            )
        workflow["stages"].append(
            _stage(
                "validate-tool-args",
                "工具參數驗證",
                "completed",
                issueCount=0,
                confirmationRequired=False,
                confirmationReason="read-only preview",
            )
        )

        plan = self.tool(model_args)
        workflow["stages"].append(
            _stage(
                "execute-tool",
                "執行確定性排程工具",
                "completed",
                tool=TOOL_NAME,
                sessionCount=len(plan["sessions"]),
                scheduledMinutes=plan["scheduledMinutes"],
                remainingMinutes=plan["remainingMinutes"],
            )
        )
        raw_explanation, summary_meta = provider.summarize(history, plan)
        explanation = _validate_explanation(raw_explanation, plan["remainingMinutes"])
        workflow["stages"].append(
            _stage(
                "return-tool-result",
                "工具結果回送 Gemini",
                "completed",
                functionResponseCount=1,
                citationCount=len(explanation["citations"]),
            )
        )
        workflow.update(status="completed", stopReason=None)
        return {
            "plan": plan,
            "agent": {
                **explanation,
                "framework": "Google Cloud Vertex AI / ADC",
                "tool": TOOL_NAME,
                "model": provider.config.model,
                "usage": {
                    "toolSelection": selection_meta.get("usage", {}),
                    "finalSummary": summary_meta.get("usage", {}),
                },
            },
            "comparison": {
                "rulePreserved": True,
                "scheduledMinutes": plan["scheduledMinutes"],
                "remainingMinutes": plan["remainingMinutes"],
                "sessionCount": len(plan["sessions"]),
            },
            "workflow": workflow,
        }


def _service() -> StudyAgentService:
    factory = current_app.config.get("STUDY_AGENT_SERVICE_FACTORY")
    return factory() if factory else StudyAgentService()


@routes.get("/health")
def health():
    return {
        "ok": True,
        "provider": "Google Cloud Vertex AI Gemini",
        "authentication": "Application Default Credentials",
        "projectConfigured": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
        "modelConfigured": bool(
            os.getenv("GOOGLE_CLOUD_GEMINI_MODEL") or os.getenv("GEMINI_MODEL")
        ),
        "liveChecked": False,
    }


@routes.post("/run")
def run_study_agent():
    try:
        result = _service().run(request.get_json(silent=True))
        return jsonify(result), 200
    except StudyAgentError as error:
        return (
            jsonify(
                {
                    "error": str(error),
                    "code": error.code,
                    "workflow": error.workflow,
                    **({"issues": error.issues} if error.issues else {}),
                }
            ),
            error.status,
        )
    except VertexProviderError as error:
        status = 503 if not error.attempted else 502
        return (
            jsonify(
                {
                    "error": "Gemini / ADC 尚未可用，原本規則排程仍可使用。",
                    "code": error.code,
                }
            ),
            status,
        )
    except (ValueError, TypeError, KeyError):
        current_app.logger.exception("Study agent output validation failed")
        return (
            jsonify(
                {
                    "error": "Agent 結果未通過驗證，原本規則排程仍可使用。",
                    "code": "AGENT_OUTPUT_INVALID",
                }
            ),
            502,
        )
