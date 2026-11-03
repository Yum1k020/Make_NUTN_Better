from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Callable

from backend.week04_tools import preview_study_plan

Extractor = Callable[[str], dict[str, Any]]
Summarizer = Callable[[dict[str, Any]], str]
PreviewTool = Callable[..., dict[str, Any]]

_REQUIRED_FIELDS = (
    "plan_id",
    "start_date",
    "exam_date",
    "target_minutes",
    "session_minutes",
    "allowed_windows",
    "busy_intervals",
)


def _validate_request(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["extractor output must be an object"]

    missing = [field for field in _REQUIRED_FIELDS if field not in payload]
    if missing:
        errors.append("missing required fields: " + ", ".join(sorted(missing)))
        return errors

    if not isinstance(payload["plan_id"], str) or not payload["plan_id"].strip():
        errors.append("plan_id must be a non-empty string")

    for field in ("target_minutes", "session_minutes"):
        value = payload[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"{field} must be a positive integer")

    try:
        start = date.fromisoformat(str(payload["start_date"]))
        exam = date.fromisoformat(str(payload["exam_date"]))
        if start >= exam:
            errors.append("start_date must be earlier than exam_date")
    except ValueError:
        errors.append("start_date and exam_date must use YYYY-MM-DD")

    windows = payload["allowed_windows"]
    if not isinstance(windows, list) or not windows:
        errors.append("allowed_windows must be a non-empty list")
    else:
        for index, window in enumerate(windows):
            if not isinstance(window, dict):
                errors.append(f"allowed_windows[{index}] must be an object")
                continue
            if "start_time" not in window or "end_time" not in window:
                errors.append(f"allowed_windows[{index}] requires start_time and end_time")
                continue
            try:
                start_t = time.fromisoformat(str(window["start_time"]))
                end_t = time.fromisoformat(str(window["end_time"]))
                if end_t <= start_t:
                    errors.append(f"allowed_windows[{index}] end_time must be later than start_time")
            except ValueError:
                errors.append(f"allowed_windows[{index}] has invalid time")

            if window.get("date") is not None:
                try:
                    date.fromisoformat(str(window["date"]))
                except ValueError:
                    errors.append(f"allowed_windows[{index}] has invalid date")

            if window.get("weekday") is not None:
                try:
                    weekday = int(window["weekday"])
                except (TypeError, ValueError):
                    errors.append(f"allowed_windows[{index}] weekday must be 1..7")
                else:
                    if weekday < 1 or weekday > 7:
                        errors.append(f"allowed_windows[{index}] weekday must be 1..7")

    busy = payload["busy_intervals"]
    if not isinstance(busy, list):
        errors.append("busy_intervals must be a list")
    else:
        for index, item in enumerate(busy):
            if not isinstance(item, dict):
                errors.append(f"busy_intervals[{index}] must be an object")
                continue
            if "starts_at" not in item or "ends_at" not in item:
                errors.append(f"busy_intervals[{index}] requires starts_at and ends_at")
                continue
            try:
                starts_at = datetime.fromisoformat(str(item["starts_at"]))
                ends_at = datetime.fromisoformat(str(item["ends_at"]))
                if ends_at <= starts_at:
                    errors.append(f"busy_intervals[{index}] ends_at must be later than starts_at")
            except ValueError:
                errors.append(f"busy_intervals[{index}] has invalid datetime")

    return errors


def _result(
    *,
    status: str,
    stop_reason: str,
    trace: list[dict[str, Any]],
    counts: dict[str, int],
    extracted_request: dict[str, Any] | None = None,
    preview: dict[str, Any] | None = None,
    answer: str | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "workflow": "prompt_chaining",
        "status": status,
        "stop_reason": stop_reason,
        "extracted_request": extracted_request,
        "preview": preview,
        "answer": answer,
        "errors": errors or [],
        "counts": dict(counts),
        "trace": trace,
    }


def run_study_plan_chaining(
    *,
    user_text: str,
    extractor: Extractor,
    summarizer: Summarizer,
    preview_tool: PreviewTool = preview_study_plan,
) -> dict[str, Any]:
    """Week 06 prompt-chaining workflow.

    Stage 0: reject an empty user request.
    Stage 1: extract a structured study-plan request.
    Gate: validate the extraction before any business tool runs.
    Stage 2: run the existing read-only study-plan preview tool.
    Stage 3: summarize only the verified tool result.
    """

    trace: list[dict[str, Any]] = []
    counts = {"extractor_calls": 0, "preview_tool_calls": 0, "summarizer_calls": 0}

    if not isinstance(user_text, str) or not user_text.strip():
        trace.append({"stage": "input", "status": "rejected", "reason": "empty_user_text"})
        return _result(
            status="rejected",
            stop_reason="invalid_input",
            trace=trace,
            counts=counts,
            errors=["user_text must not be empty"],
        )

    counts["extractor_calls"] += 1
    trace.append({"stage": "extract", "status": "started"})
    try:
        extracted = extractor(user_text)
    except Exception as exc:
        trace.append({
            "stage": "extract",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        return _result(
            status="failed",
            stop_reason="provider_failure",
            trace=trace,
            counts=counts,
            errors=[str(exc)],
        )

    trace.append({"stage": "extract", "status": "completed", "result": extracted})

    gate_errors = _validate_request(extracted)
    if gate_errors:
        trace.append({
            "stage": "gate",
            "status": "rejected",
            "errors": gate_errors,
            "downstream_calls": 0,
        })
        return _result(
            status="rejected",
            stop_reason="gate_rejected",
            trace=trace,
            counts=counts,
            extracted_request=extracted if isinstance(extracted, dict) else None,
            errors=gate_errors,
        )

    trace.append({"stage": "gate", "status": "passed"})

    counts["preview_tool_calls"] += 1
    trace.append({"stage": "preview_tool", "status": "started", "tool": "preview_study_plan"})
    try:
        preview = preview_tool(**extracted)
    except Exception as exc:
        trace.append({
            "stage": "preview_tool",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        return _result(
            status="failed",
            stop_reason="tool_failure",
            trace=trace,
            counts=counts,
            extracted_request=extracted,
            errors=[str(exc)],
        )

    trace.append({
        "stage": "preview_tool",
        "status": "completed",
        "tool": "preview_study_plan",
        "result": preview,
    })

    counts["summarizer_calls"] += 1
    trace.append({"stage": "summarize", "status": "started"})
    try:
        answer = summarizer(preview)
    except Exception as exc:
        trace.append({
            "stage": "summarize",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        return _result(
            status="failed",
            stop_reason="provider_failure_after_tool",
            trace=trace,
            counts=counts,
            extracted_request=extracted,
            preview=preview,
            errors=[str(exc)],
        )

    if not isinstance(answer, str) or not answer.strip():
        trace.append({"stage": "summarize", "status": "failed", "error": "empty summary"})
        return _result(
            status="failed",
            stop_reason="invalid_summary",
            trace=trace,
            counts=counts,
            extracted_request=extracted,
            preview=preview,
            errors=["summarizer returned an empty answer"],
        )

    trace.append({"stage": "summarize", "status": "completed", "answer": answer})
    return _result(
        status="answer_ready",
        stop_reason="completed",
        trace=trace,
        counts=counts,
        extracted_request=extracted,
        preview=preview,
        answer=answer,
    )
