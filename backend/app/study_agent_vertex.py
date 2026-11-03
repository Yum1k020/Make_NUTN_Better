"""Vertex AI Gemini adapter authenticated only through Google Cloud ADC."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any


CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
TOOL_NAME = "get_validated_study_plan"
_RESOURCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class VertexProviderError(RuntimeError):
    def __init__(self, code: str, *, attempted: bool = False):
        super().__init__(code)
        self.code = code
        self.attempted = attempted


@dataclass(frozen=True)
class VertexConfig:
    project: str
    location: str
    model: str

    @property
    def endpoint(self) -> str:
        host = (
            "aiplatform.googleapis.com"
            if self.location == "global"
            else f"{self.location}-aiplatform.googleapis.com"
        )
        return (
            f"https://{host}/v1/projects/{self.project}/locations/{self.location}"
            f"/publishers/google/models/{self.model}:generateContent"
        )


def load_vertex_config(*, project: str | None = None) -> VertexConfig:
    configured_project = (project or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
    location = (os.getenv("GOOGLE_CLOUD_LOCATION") or "global").strip()
    model = (
        os.getenv("GOOGLE_CLOUD_GEMINI_MODEL")
        or os.getenv("GEMINI_MODEL")
        or ""
    ).strip()
    if not configured_project:
        raise VertexProviderError("GOOGLE_CLOUD_PROJECT_NOT_CONFIGURED")
    if not model:
        raise VertexProviderError("GOOGLE_CLOUD_GEMINI_MODEL_NOT_CONFIGURED")
    for label, value in (
        ("GOOGLE_CLOUD_PROJECT", configured_project),
        ("GOOGLE_CLOUD_LOCATION", location),
        ("GOOGLE_CLOUD_GEMINI_MODEL", model),
    ):
        if not _RESOURCE_RE.fullmatch(value):
            raise VertexProviderError(f"INVALID_{label}")
    return VertexConfig(configured_project, location, model)


def _tool_declaration() -> dict[str, Any]:
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
        },
    }


class VertexGeminiADCClient:
    """Two-turn manual function-calling client for the study-plan preview."""

    def __init__(
        self,
        *,
        config: VertexConfig | None = None,
        session: Any | None = None,
        timeout: int = 45,
    ) -> None:
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        self.config = config or load_vertex_config()
        if session is None:
            try:
                import google.auth
                from google.auth.exceptions import DefaultCredentialsError
                from google.auth.transport.requests import AuthorizedSession
            except ImportError as error:
                raise VertexProviderError("ADC_DEPENDENCY_NOT_INSTALLED") from error
            try:
                credentials, _adc_project = google.auth.default(
                    scopes=[CLOUD_PLATFORM_SCOPE]
                )
                session = AuthorizedSession(credentials)
            except DefaultCredentialsError as error:
                raise VertexProviderError("ADC_NOT_CONFIGURED") from error
        self.session = session

    def _post(self, stage: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.session.post(
                self.config.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            code = f"VERTEX_HTTP_{status}" if status else "VERTEX_UNAVAILABLE"
            raise VertexProviderError(code, attempted=True) from error
        self.calls.append(
            {
                "stage": stage,
                "model": self.config.model,
                "usage": result.get("usageMetadata", {}),
            }
        )
        return result

    @staticmethod
    def _content(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return payload["candidates"][0]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise VertexProviderError(
                "VERTEX_INVALID_RESPONSE", attempted=True
            ) from error

    @staticmethod
    def _text(payload: dict[str, Any]) -> str:
        content = VertexGeminiADCClient._content(payload)
        text = "\n".join(
            part.get("text", "")
            for part in content.get("parts", [])
            if isinstance(part, dict) and part.get("text") and not part.get("thought")
        ).strip()
        if not text:
            raise VertexProviderError("VERTEX_MISSING_TEXT", attempted=True)
        return text

    def choose_tool(
        self, request_data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        user_content = {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "你是學生個人安排系統的工具選擇階段。"
                        f"請呼叫 {TOOL_NAME}，參數必須逐欄等於下方已驗證需求；"
                        "不得補猜、刪除或改寫。\n"
                        + json.dumps(request_data, ensure_ascii=False, sort_keys=True)
                    )
                }
            ],
        }
        payload = self._post(
            "tool_selection",
            {
                "contents": [user_content],
                "tools": [{"functionDeclarations": [_tool_declaration()]}],
                "toolConfig": {
                    "functionCallingConfig": {
                        "mode": "ANY",
                        "allowedFunctionNames": [TOOL_NAME],
                    }
                },
                "generationConfig": {"temperature": 0, "maxOutputTokens": 1024},
            },
        )
        model_content = self._content(payload)
        calls = [
            part["functionCall"]
            for part in model_content.get("parts", [])
            if isinstance(part, dict) and isinstance(part.get("functionCall"), dict)
        ]
        if len(calls) != 1:
            raise VertexProviderError("EXPECTED_ONE_FUNCTION_CALL", attempted=True)
        return calls[0], [user_content, model_content], self.calls[-1]

    def summarize(
        self,
        history: list[dict[str, Any]],
        tool_result: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        function_response = {
            "role": "tool",
            "parts": [
                {
                    "functionResponse": {
                        "name": TOOL_NAME,
                        "response": {"result": tool_result},
                    }
                }
            ],
        }
        payload = self._post(
            "final_summary",
            {
                "contents": [*history, function_response],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": (
                                "只能根據 functionResponse 的已驗證排程回答。"
                                "輸出單一 JSON 物件，欄位為 summary、warnings、citations、refused。"
                                "summary 使用繁體中文且不超過 300 字。"
                                "warnings 是字串陣列；剩餘分鐘為 0 時必須是空陣列。"
                                "citations 只能包含 planner-rule、weekly-classes-fixture、tasks-events-local。"
                                "refused 在正常輸入時為 false。不得改寫任何排程時段。"
                            )
                        }
                    ]
                },
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 1200,
                    "responseMimeType": "application/json",
                },
            },
        )
        try:
            result = json.loads(self._text(payload))
        except (json.JSONDecodeError, TypeError) as error:
            raise VertexProviderError(
                "VERTEX_INVALID_STRUCTURED_OUTPUT", attempted=True
            ) from error
        return result, self.calls[-1]
