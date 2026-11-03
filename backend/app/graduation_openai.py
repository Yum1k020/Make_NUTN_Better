"""OpenAI adapter for user-authorized aggregate graduation facts only.

The API key stays on the Flask server. The model receives the bounded,
de-identified projection produced by ``evidence_context`` and must return the
same facts in a strict JSON schema before the local evaluator accepts them.
"""

from __future__ import annotations

import json
import os
from hashlib import sha256
from time import perf_counter
from typing import Any

import requests

from .graduation_explanation_core import ProviderFailure, valid_draft
from .planner_core import dump
from .study_agent_openai import (
    DEFAULT_OPENAI_MODEL,
    OPENAI_RESPONSES_ENDPOINT,
    load_openai_config,
)


def _response_format(context: dict[str, Any]) -> dict[str, Any]:
    item_count = len(context["checks"])
    return {
        "type": "json_schema",
        "name": "graduation_explanation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "rule_set_id": {"type": "string"},
                "overall_status": {
                    "type": "string",
                    "enum": ["met", "not_met", "needs_confirmation"],
                },
                "earned_credits": {"type": ["number", "null"]},
                "scope": {"type": "string", "enum": ["project_rules_only"]},
                "items": {
                    "type": "array",
                    "minItems": item_count,
                    "maxItems": item_count,
                    "items": {
                        "type": "object",
                        "properties": {
                            "check_id": {"type": "string"},
                            "actual_value": {"type": ["number", "null"]},
                            "remaining_value": {"type": ["number", "null"]},
                            "status": {
                                "type": "string",
                                "enum": ["met", "not_met", "needs_confirmation"],
                            },
                            "source_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": 1,
                            },
                            "action": {
                                "type": "string",
                                "enum": [
                                    "keep_record",
                                    "review_requirement",
                                    "provide_evidence",
                                ],
                            },
                        },
                        "required": [
                            "check_id",
                            "actual_value",
                            "remaining_value",
                            "status",
                            "source_ids",
                            "action",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "rule_set_id",
                "overall_status",
                "earned_credits",
                "scope",
                "items",
            ],
            "additionalProperties": False,
        },
    }


def _output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, list):
        raise ProviderFailure("PROVIDER_INVALID_RESPONSE", attempted=True)
    parts = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        parts.extend(
            part["text"]
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "output_text"
            and isinstance(part.get("text"), str)
        )
    text = "\n".join(parts).strip()
    if not text:
        raise ProviderFailure("PROVIDER_INVALID_RESPONSE", attempted=True)
    return text


def generate(context, previous, feedback):
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not key.strip():
        raise ProviderFailure("PROVIDER_NOT_CONFIGURED")
    try:
        config = load_openai_config()
    except Exception as error:
        code = getattr(error, "code", "INVALID_MODEL_CONFIG")
        raise ProviderFailure(code) from None

    prompt = {
        "task": (
            "依證據產生畢業缺項的結構化說明。全部 checks 必須各出現一次；"
            "逐字保留數值、null、狀態及規則版本，不得新增事實。"
        ),
        "evidence": context,
        "output_example": valid_draft(context),
        "previous_draft": previous,
        "evaluation_errors": feedback,
    }
    payload = {
        "model": config.model,
        "instructions": (
            "只能根據 input 的 evidence 輸出 JSON。每項 source_ids 必須為 "
            "[rule_set_id + ':' + check_id]；action 對照為 met=keep_record、"
            "not_met=review_requirement、needs_confirmation=provide_evidence。"
            "不得輸出推理過程或額外文字。"
        ),
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": dump(prompt)}],
            }
        ],
        "text": {"format": _response_format(context)},
        "max_output_tokens": 8192,
        "store": False,
    }
    started = perf_counter()
    try:
        response = requests.Session().post(
            OPENAI_RESPONSES_ENDPOINT,
            json=payload,
            timeout=45,
            headers={
                "Authorization": f"Bearer {key.strip()}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ProviderFailure("PROVIDER_INVALID_RESPONSE", attempted=True)
        try:
            draft = json.loads(_output_text(result))
        except (json.JSONDecodeError, TypeError):
            draft = None
        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        encoded = dump(payload).encode()
        return draft, {
            "provider": "openai",
            "model": config.model or DEFAULT_OPENAI_MODEL,
            "actual_call": {
                "method": "POST",
                "endpoint": OPENAI_RESPONSES_ENDPOINT,
                "request_sha256": sha256(encoded).hexdigest(),
                "tool_result_delivery": "graduation_progress aggregate in input",
            },
            "latency_ms": round((perf_counter() - started) * 1000),
            "usage": {
                key: usage[key]
                for key in ("input_tokens", "output_tokens", "total_tokens")
                if key in usage
            },
        }
    except ProviderFailure:
        raise
    except requests.HTTPError as error:
        status = getattr(error.response, "status_code", None)
        code = f"PROVIDER_HTTP_{status}" if status else "PROVIDER_UNAVAILABLE"
        raise ProviderFailure(code, attempted=True) from None
    except (requests.RequestException, TimeoutError, OSError, ValueError, TypeError):
        raise ProviderFailure("PROVIDER_UNAVAILABLE", attempted=True) from None
