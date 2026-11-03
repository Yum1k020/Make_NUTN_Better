from __future__ import annotations

import json
from typing import Any

import requests


RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIChainingClient:
    def __init__(self, *, api_key: str, model: str, timeout: int = 45):
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        if not self.api_key:
            raise ValueError("api_key is required")
        if not self.model:
            raise ValueError("model is required")

    def _call(
        self,
        *,
        stage: str,
        prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            "store": False,
        }
        if response_format:
            body["text"] = {"format": response_format}
        try:
            response = requests.post(
                RESPONSES_URL,
                json=body,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", "unknown")
            raise RuntimeError(f"OpenAI HTTP {status}") from None
        except requests.RequestException:
            raise RuntimeError("OpenAI connection error") from None

        self.calls.append(
            {"stage": stage, "model": self.model, "usage": payload.get("usage")}
        )
        return payload

    @staticmethod
    def _text(payload: dict[str, Any]) -> str:
        parts = []
        for item in payload.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            parts.extend(
                part["text"]
                for part in item.get("content", [])
                if isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            )
        text = "\n".join(parts).strip()
        if not text:
            raise RuntimeError("OpenAI response did not contain text")
        return text

    def extract_study_plan_request(self, user_text: str) -> dict[str, Any]:
        prompt = f"""
You are the extraction stage of a student study-planning workflow.
Convert the user's request into exactly one JSON object with these keys:
plan_id, start_date, exam_date, target_minutes, session_minutes,
allowed_windows, busy_intervals.

Rules:
- Do not invent missing facts.
- Dates must be YYYY-MM-DD.
- Times must be HH:MM.
- busy_intervals starts_at/ends_at must be ISO local datetime strings.
- Keep busy interval metadata such as source_type/source_id/title when provided.

User request:
{user_text}
""".strip()
        response_format = {
            "type": "json_schema",
            "name": "study_plan_request",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "start_date": {"type": "string"},
                    "exam_date": {"type": "string"},
                    "target_minutes": {"type": "integer"},
                    "session_minutes": {"type": "integer"},
                    "allowed_windows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "start_time": {"type": "string"},
                                "end_time": {"type": "string"},
                            },
                            "required": ["date", "start_time", "end_time"],
                            "additionalProperties": False,
                        },
                    },
                    "busy_intervals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "starts_at": {"type": "string"},
                                "ends_at": {"type": "string"},
                                "source_type": {"type": ["string", "null"]},
                                "source_id": {"type": ["string", "null"]},
                                "title": {"type": ["string", "null"]},
                            },
                            "required": [
                                "starts_at",
                                "ends_at",
                                "source_type",
                                "source_id",
                                "title",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "plan_id",
                    "start_date",
                    "exam_date",
                    "target_minutes",
                    "session_minutes",
                    "allowed_windows",
                    "busy_intervals",
                ],
                "additionalProperties": False,
            },
        }
        payload = self._call(
            stage="extract", prompt=prompt, response_format=response_format
        )
        try:
            result = json.loads(self._text(payload))
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI extraction was not valid JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("OpenAI extraction was not a JSON object")
        return result

    def summarize_preview(self, preview: dict[str, Any]) -> str:
        prompt = (
            "你是學生複習排程 workflow 的最後摘要階段。"
            "只能根據下方已驗證的 preview JSON 回答，不可補猜。"
            "請用繁體中文簡短說明已安排分鐘數、剩餘分鐘數、時段，"
            "並明確說明這只是預覽、尚未寫入。\n\n"
            + json.dumps(preview, ensure_ascii=False, indent=2)
        )
        return self._text(self._call(stage="summarize", prompt=prompt))
