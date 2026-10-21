from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class GeminiChainingClient:
    def __init__(self, *, api_key: str, model: str, timeout: int = 45):
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        if not self.api_key:
            raise ValueError("api_key is required")
        if not self.model:
            raise ValueError("model is required")

    def _call(self, *, stage: str, body: dict[str, Any]) -> dict[str, Any]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        req = request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Gemini connection error: {exc.reason}") from exc

        self.calls.append({
            "stage": stage,
            "model": self.model,
            "usage_metadata": payload.get("usageMetadata"),
        })
        return payload

    @staticmethod
    def _text(payload: dict[str, Any]) -> str:
        try:
            parts = payload["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Gemini response missing candidate content") from exc

        text = "\n".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("text")
        ).strip()
        if not text:
            raise RuntimeError("Gemini response did not contain text")
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
- Output JSON only.

User request:
{user_text}
""".strip()

        payload = self._call(
            stage="extract",
            body={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
        )
        text = self._text(payload)
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini extraction was not valid JSON") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Gemini extraction was not a JSON object")
        return result

    def summarize_preview(self, preview: dict[str, Any]) -> str:
        prompt = (
            "你是學生複習排程 workflow 的最後摘要階段。"
            "只能根據下方已驗證的 preview JSON 回答，不可補猜。"
            "請用繁體中文簡短說明已安排分鐘數、剩餘分鐘數、時段，"
            "並明確說明這只是預覽、尚未寫入。\n\n"
            + json.dumps(preview, ensure_ascii=False, indent=2)
        )
        payload = self._call(
            stage="summarize",
            body={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0},
            },
        )
        return self._text(payload)
