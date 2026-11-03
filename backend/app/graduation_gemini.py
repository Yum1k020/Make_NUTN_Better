"""Gemini REST adapter for user-authorized aggregate graduation facts only.

Reference: https://ai.google.dev/api/generate-content
Key/model are server-side environment settings, never accepted from the browser.
"""

import json
import os
import re
import socket
from hashlib import sha256
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .graduation_explanation_core import ProviderFailure, valid_draft
from .planner_core import dump


def generate(context, previous, feedback):
    key, model = os.environ.get("GEMINI_API_KEY"), os.environ.get("GEMINI_MODEL")
    if not key or not model:
        raise ProviderFailure("PROVIDER_NOT_CONFIGURED")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", model):
        raise ProviderFailure("INVALID_MODEL_CONFIG")
    prompt = {"task": "依證據產生畢業缺項的結構化說明。全部 checks 必須各出現一次；優先列未達標與待確認。"
              "逐字保留數值、null、狀態及規則版本；不得新增欄位或自由文字。每項 source_ids 必須為 [rule_set_id + ':' + check_id]。"
              "action 對照：met=keep_record, not_met=review_requirement, needs_confirmation=provide_evidence。"
              "scope 必須為 project_rules_only。只輸出 JSON，禁止推理過程。",
              "evidence": context, "output_example": valid_draft(context),
              "previous_draft": previous, "evaluation_errors": feedback}
    payload = {"contents": [{"role": "user", "parts": [{"text": dump(prompt)}]}],
               "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                                    "maxOutputTokens": 8192}}
    req = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  data=dump(payload).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    started = perf_counter()
    try:
        with urlopen(req, timeout=25) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise ProviderFailure("PROVIDER_RESPONSE_TOO_LARGE", attempted=True)
        result = json.loads(raw)
        candidate = result.get("candidates", [{}])[0]
        if candidate.get("finishReason") != "STOP":
            raise ProviderFailure("PROVIDER_INCOMPLETE", attempted=True)
        # Do not use or persist provider thought parts.
        text = "".join(p.get("text", "") for p in candidate["content"]["parts"] if not p.get("thought"))
        try:
            draft = json.loads(text)
        except (ValueError, TypeError):
            draft = None
        usage = result.get("usageMetadata", {})
        return draft, {"provider": "gemini", "model": model,
                       "actual_call": {"method": "POST", "endpoint": req.full_url,
                                       "request_sha256": sha256(req.data).hexdigest(),
                                       "tool_result_delivery": "graduation_progress aggregate in contents.evidence"},
                       "latency_ms": round((perf_counter() - started) * 1000),
                       "usage": {k: usage[k] for k in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount") if k in usage}}
    except HTTPError as error:
        raise ProviderFailure("PROVIDER_HTTP_" + str(error.code), attempted=True) from None
    except (URLError, TimeoutError, socket.timeout, OSError):
        raise ProviderFailure("PROVIDER_UNAVAILABLE", attempted=True) from None
    except (ValueError, TypeError, KeyError, IndexError):
        raise ProviderFailure("PROVIDER_INVALID_RESPONSE", attempted=True) from None
