"""Local evaluator/optimizer. Providers are explicit dependencies, never implicit I/O."""

from copy import deepcopy
from hashlib import sha256
from time import perf_counter
from uuid import uuid4

from .planner_core import dump, timestamp

RUBRIC = "graduation-explanation-v1"
ACTIONS = {"met": "keep_record", "not_met": "review_requirement",
           "needs_confirmation": "provide_evidence"}
STATUS = {"met": "已達標", "not_met": "未達標", "needs_confirmation": "待確認"}
NEXT = {"keep_record": "保留通過與認列紀錄。",
        "review_requirement": "查看此項要求，確認補修或補足方式；開課資訊需另行查證。",
        "provide_evidence": "補齊通過、分類或認列等證據，再重新檢查。"}
CHECK_NAMES = {"general_core": "通識核心", "general_domain": "通識領域學分", "college_required": "院核心",
               "department_required": "專業必修學分", "department_elective": "專業選修", "free_elective": "自由選修"}
UNITS = {"credits": "學分", "courses": "門", "lectures": "場", "programs": "個學程", "domains": "個領域"}
CLAIM_KEYS = {"check_id", "actual_value", "remaining_value", "status", "source_ids", "action"}
TOP_KEYS = {"rule_set_id", "overall_status", "earned_credits", "scope", "items"}


class ProviderFailure(Exception):
    def __init__(self, code, attempted=False):
        self.code, self.attempted = code, attempted


def evidence_context(result):
    """Only aggregate facts needed to explain a run; exclude identity and raw records."""
    return {"rule_set_id": result["rule_set_id"],
            "overall_status": result["overall_status"],
            "earned_credits": result["earned_credits"], "scope": "project_rules_only",
            "checks": [{key: c[key] for key in (
                "check_id", "name", "actual_value", "remaining_value", "required_value", "unit", "status")}
                for c in result["checks"]]}


def source_id(context, check_id):
    return context["rule_set_id"] + ":" + check_id


def valid_draft(context):
    """Deterministic fallback, also documents the exact structured output contract."""
    return {key: context[key] for key in TOP_KEYS - {"items"}} | {"items": [
        {**{key: c[key] for key in ("check_id", "actual_value", "remaining_value", "status")},
         "source_ids": [source_id(context, c["check_id"])], "action": ACTIONS[c["status"]]}
        for c in context["checks"]]}


def evaluate(draft, context):
    """Closed-world rubric, identical for A and B. Unknown is never zero."""
    errors = []
    if type(draft) is not dict or set(draft) != TOP_KEYS:
        return ["INVALID_TOP_LEVEL_SCHEMA"]
    for key in TOP_KEYS - {"items"}:
        if dump(draft[key]) != dump(context[key]):
            errors.append("FACT_MISMATCH:" + key)
    items = draft["items"]
    if type(items) is not list or len(items) != len(context["checks"]):
        return errors + ["CHECK_COVERAGE"]
    checks = {c["check_id"]: c for c in context["checks"]}
    seen = set()
    for item in items:
        if type(item) is not dict or set(item) != CLAIM_KEYS:
            errors.append("INVALID_CLAIM_SCHEMA")
            continue
        cid = item["check_id"]
        if type(cid) is not str or cid not in checks or cid in seen:
            errors.append("UNKNOWN_OR_DUPLICATE_CHECK")
            continue
        seen.add(cid)
        check = checks[cid]
        for key in ("actual_value", "remaining_value", "status"):
            if dump(item[key]) != dump(check[key]):
                errors.append("FACT_MISMATCH:" + cid + ":" + key)
        if item["source_ids"] != [source_id(context, cid)]:
            errors.append("SOURCE_MISMATCH:" + cid)
        if item["action"] != ACTIONS[check["status"]]:
            errors.append("UNSUPPORTED_ACTION:" + cid)
    if seen != set(checks):
        errors.append("CHECK_COVERAGE")
    return errors


def render(draft, context):
    """Render verified structured clauses; never display unchecked model prose."""
    checks = {c["check_id"]: c for c in context["checks"]}
    rendered = []
    for item in draft["items"]:
        c = checks[item["check_id"]]
        amount = "資料未知，不能當作零或已達標。" if c["actual_value"] is None else (
            f"已採計 {c['actual_value']:g}／要求 {c['required_value']:g}，尚缺 {c['remaining_value']:g}（{UNITS.get(c['unit'], c['unit'])}）。")
        rendered.append({"check_id": c["check_id"], "name": CHECK_NAMES.get(c["check_id"], c["name"]),
                         "text": f"{STATUS[c['status']]}：{amount}",
                         "next_step": NEXT[item["action"]], "source_ids": item["source_ids"]})
    return rendered


def explain(result, provider):
    context = evidence_context(result)
    started = perf_counter()
    output = {"run_id": str(uuid4()), "evaluated_at": timestamp(), "rubric": RUBRIC,
              "evidence_sha256": sha256(dump(context).encode()).hexdigest(),
              "evidence": context, "attempts": [], "model_calls": 0,
              "tool_calls": 1, "tool": "graduation_progress", "status": "fallback",
              "stop_reason": "RULE_UNAVAILABLE", "explanation": [],
              "scope_text": "符合本次啟用的專案規則不等於校方畢業認證；規劃中或修習中課程不算已取得學分。"}
    if result["rule_set_id"] and context["checks"]:
        previous, feedback = None, []
        for attempt in range(2):
            try:
                draft, metrics = provider(deepcopy(context), deepcopy(previous), feedback[:])
                output["model_calls"] += 1
            except ProviderFailure as error:
                output["model_calls"] += int(error.attempted)
                output["stop_reason"] = error.code
                break
            try:
                feedback = evaluate(draft, context)
            except (ValueError, TypeError, OverflowError):
                feedback, draft = ["INVALID_JSON_VALUES"], None
            output["attempts"].append({"label": "A" if attempt == 0 else "B", "draft": draft,
                                       "errors": feedback[:], "passed": not feedback, "metrics": metrics})
            if not feedback:
                output.update(status="verified", stop_reason="RUBRIC_PASS", explanation=render(draft, context))
                break
            previous = draft
            output["stop_reason"] = "REVISION_LIMIT"
        if output["status"] != "verified":
            output["explanation"] = render(valid_draft(context), context)
    output["latency_ms"] = round((perf_counter() - started) * 1000)
    return output
