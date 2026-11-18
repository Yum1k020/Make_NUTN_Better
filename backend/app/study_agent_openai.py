"""OpenAI Responses API adapter for the study-planning tool loop."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .study_agent_contract import (
    TOOL_NAME,
    StudyAgentProviderError,
    tool_declaration,
)


OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
EXPERT_CONTEXT_BASELINE = "week08-instruction-v1"
EXPERT_CONTEXT_CANDIDATE = "week09-few-shot-v1"


class OpenAIProviderError(StudyAgentProviderError):
    pass


@dataclass(frozen=True)
class OpenAIConfig:
    model: str
    endpoint: str = OPENAI_RESPONSES_ENDPOINT


def load_openai_config() -> OpenAIConfig:
    model = (os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL).strip()
    if not model or len(model) > 120 or any(character.isspace() for character in model):
        raise OpenAIProviderError("INVALID_OPENAI_MODEL")
    return OpenAIConfig(model=model)


def _response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "study_plan_explanation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "maxLength": 600},
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
                "citations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "planner-rule",
                            "weekly-classes-fixture",
                            "planner-backend-sqlite",
                        ],
                    },
                    "minItems": 1,
                },
                "refused": {"type": "boolean"},
            },
            "required": ["summary", "warnings", "citations", "refused"],
            "additionalProperties": False,
        },
    }



def _expert_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "study_load_expert_review",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "assessment": {
                    "type": "string",
                    "enum": ["balanced", "concentrated", "insufficient"],
                },
                "summary": {"type": "string", "maxLength": 400},
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
                "citations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["planner-rule", "study-load-review"],
                    },
                    "minItems": 1,
                },
            },
            "required": [
                "assessment",
                "summary",
                "recommendations",
                "citations",
            ],
            "additionalProperties": False,
        },
    }

def _expert_instructions(context_variant: str) -> str:
    baseline = (
        "你是獨立的 Study Load Review Expert。只檢查收到的去識別讀書計畫，"
        "不得要求額外資料、不得呼叫工具、不得修改排程或資料庫。"
        "assessment=insufficient 只用於 remainingMinutes>0；"
        "若已排滿，再依時段是否過度集中選 balanced 或 concentrated。"
        "recommendations 最多三項，必須是非寫入的建議。"
        "citations 只能使用 planner-rule 或 study-load-review。"
    )
    if context_variant == EXPERT_CONTEXT_BASELINE:
        return baseline
    if context_variant != EXPERT_CONTEXT_CANDIDATE:
        raise ValueError("Unknown expert context variant.")

    few_shot = (
        "\n\nWeek 09 few-shot 規則："
        "先依 deterministic facts 判斷 assessment。"
        "remainingMinutes>0 必須是 insufficient。"
        "若 remainingMinutes=0，先按日期加總 sessions 分鐘；"
        "任一日期占 scheduledMinutes 的三分之二以上時為 concentrated，"
        "否則為 balanced。"
        "\nFew-shot 1｜輸入：scheduledMinutes=240、remainingMinutes=120，"
        "sessions 分散在兩天。輸出：assessment=insufficient；"
        "summary 說明仍有 120 分鐘未排；recommendations 建議增加可用時段。"
        "\nFew-shot 2｜輸入：scheduledMinutes=360、remainingMinutes=0，"
        "三個 120 分鐘 sessions 全在同一天。輸出：assessment=concentrated；"
        "summary 說明時數雖排滿但集中同一天；recommendations 建議若條件允許可分散。"
        "\nFew-shot 3｜輸入：scheduledMinutes=360、remainingMinutes=0，"
        "三個 120 分鐘 sessions 分布在三天。輸出：assessment=balanced；"
        "summary 說明時數已排滿且分散。"
    )
    return baseline + few_shot


def _openai_tool() -> dict[str, Any]:
    return {"type": "function", **tool_declaration(), "strict": True}


class OpenAIResponsesClient:
    """Two-turn Responses API client with a server-only API key."""

    provider_name = "OpenAI Responses API"
    authentication = "Server-side API key"
    framework = "OpenAI Responses API"

    def __init__(
        self,
        *,
        config: OpenAIConfig | None = None,
        api_key: str | None = None,
        session: Any | None = None,
        timeout: int = 45,
    ) -> None:
        configured_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        if not configured_key or not configured_key.strip():
            raise OpenAIProviderError("OPENAI_API_KEY_NOT_CONFIGURED")
        self._api_key = configured_key.strip()
        self.config = config or load_openai_config()
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        if session is None:
            try:
                import requests
            except ImportError as error:
                raise OpenAIProviderError("OPENAI_HTTP_DEPENDENCY_NOT_INSTALLED") from error
            session = requests.Session()
        self.session = session

    def _post(self, stage: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.session.post(
                self.config.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            code = f"OPENAI_HTTP_{status}" if status else "OPENAI_UNAVAILABLE"
            raise OpenAIProviderError(code, attempted=True) from error
        if not isinstance(result, dict):
            raise OpenAIProviderError("OPENAI_INVALID_RESPONSE", attempted=True)
        self.calls.append(
            {
                "stage": stage,
                "model": self.config.model,
                "usage": result.get("usage", {}),
            }
        )
        return result

    @staticmethod
    def _output_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        output = payload.get("output")
        if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
            raise OpenAIProviderError("OPENAI_INVALID_RESPONSE", attempted=True)
        return output

    @classmethod
    def _output_text(cls, payload: dict[str, Any]) -> str:
        text_parts = []
        for item in cls._output_items(payload):
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            text_parts.extend(
                part["text"]
                for part in content
                if isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            )
        text = "\n".join(text_parts).strip()
        if not text:
            raise OpenAIProviderError("OPENAI_MISSING_TEXT", attempted=True)
        return text

    def choose_tool(
        self, request_data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "請呼叫指定的唯讀排程工具。工具參數必須逐欄等於下方已驗證需求；"
                        "不得補猜、刪除或改寫。\n"
                        + json.dumps(request_data, ensure_ascii=False, sort_keys=True)
                    ),
                }
            ],
        }
        payload = self._post(
            "tool_selection",
            {
                "model": self.config.model,
                "input": [user_message],
                "tools": [_openai_tool()],
                "tool_choice": {"type": "function", "name": TOOL_NAME},
                "parallel_tool_calls": False,
                "max_output_tokens": 1024,
                "store": False,
            },
        )
        output_items = self._output_items(payload)
        calls = [item for item in output_items if item.get("type") == "function_call"]
        if len(calls) != 1:
            raise OpenAIProviderError("EXPECTED_ONE_FUNCTION_CALL", attempted=True)
        call = calls[0]
        try:
            arguments = json.loads(call["arguments"])
            call_id = call["call_id"]
            name = call["name"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise OpenAIProviderError("OPENAI_INVALID_FUNCTION_CALL", attempted=True) from error
        if not isinstance(arguments, dict) or not isinstance(call_id, str):
            raise OpenAIProviderError("OPENAI_INVALID_FUNCTION_CALL", attempted=True)
        return (
            {"name": name, "args": arguments, "call_id": call_id},
            [user_message, *output_items],
            self.calls[-1],
        )

    def review_plan(
        self,
        packet: dict[str, Any],
        *,
        context_variant: str = EXPERT_CONTEXT_CANDIDATE,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Run the bounded expert with an explicit Week 09 context version."""

        payload = self._post(
            f"expert_review:{context_variant}",
            {
                "model": self.config.model,
                "instructions": _expert_instructions(context_variant),
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": json.dumps(
                                    packet,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                ),
                            }
                        ],
                    }
                ],
                "text": {"format": _expert_response_format()},
                "max_output_tokens": 800,
                "store": False,
            },
        )
        try:
            result = json.loads(self._output_text(payload))
        except (json.JSONDecodeError, TypeError) as error:
            raise OpenAIProviderError(
                "OPENAI_INVALID_EXPERT_OUTPUT",
                attempted=True,
            ) from error
        if not isinstance(result, dict):
            raise OpenAIProviderError(
                "OPENAI_INVALID_EXPERT_OUTPUT",
                attempted=True,
            )
        meta = {**self.calls[-1], "contextVersion": context_variant}
        return result, meta

    def summarize(
        self,
        history: list[dict[str, Any]],
        tool_result: dict[str, Any],
        expert_review: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        function_calls = [item for item in history if item.get("type") == "function_call"]
        if len(function_calls) != 1 or not isinstance(function_calls[0].get("call_id"), str):
            raise OpenAIProviderError("OPENAI_MISSING_FUNCTION_CALL", attempted=True)
        function_output = {
            "type": "function_call_output",
            "call_id": function_calls[0]["call_id"],
            "output": json.dumps(tool_result, ensure_ascii=False, sort_keys=True),
        }
        payload = self._post(
            "final_summary",
            {
                "model": self.config.model,
                "instructions": (
                    "只能根據 function_call_output 的已驗證排程回答。"
                    "summary 使用繁體中文且不超過 300 字。"
                    "warnings 是字串陣列；剩餘分鐘為 0 時必須是空陣列。"
                    "citations 只能包含 planner-rule、weekly-classes-fixture、"
                    "planner-backend-sqlite。refused 在正常輸入時為 false。"
                    "不得改寫任何排程時段。若有 Study Load Review Expert 回報，"
                    "只能整合其風險與建議，排程事實仍以 function_call_output 為準。"
                ),
                "input": [
                    *history,
                    function_output,
                    *(
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": (
                                            "受限 Study Load Review Expert 回報；"
                                            "只可把它當成建議，不得改寫 function_call_output 的排程事實：\n"
                                            + json.dumps(
                                                expert_review,
                                                ensure_ascii=False,
                                                sort_keys=True,
                                            )
                                        ),
                                    }
                                ],
                            }
                        ]
                        if expert_review is not None
                        else []
                    ),
                ],
                "tools": [_openai_tool()],
                "tool_choice": "none",
                "parallel_tool_calls": False,
                "text": {"format": _response_format()},
                "max_output_tokens": 1200,
                "store": False,
            },
        )
        try:
            result = json.loads(self._output_text(payload))
        except (json.JSONDecodeError, TypeError) as error:
            raise OpenAIProviderError(
                "OPENAI_INVALID_STRUCTURED_OUTPUT", attempted=True
            ) from error
        if not isinstance(result, dict):
            raise OpenAIProviderError("OPENAI_INVALID_STRUCTURED_OUTPUT", attempted=True)
        return result, self.calls[-1]
