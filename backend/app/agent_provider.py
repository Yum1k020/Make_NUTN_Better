"""Bounded OpenAI Responses transport; credentials and reasoning never enter traces."""

import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .planner_core import Problem


def settings():
    return {"configured": bool(os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_MODEL")),
            "model": os.environ.get("OPENAI_MODEL") or None}


def respond(instructions, messages, tools, timeout):
    config = settings()
    if not config["configured"]:
        raise Problem(503, "OPENAI_NOT_CONFIGURED", "請在後端設定 OPENAI_API_KEY 與 OPENAI_MODEL")
    payload = {"model": config["model"], "instructions": instructions, "input": messages,
               "tools": tools, "tool_choice": "required", "parallel_tool_calls": False,
               "max_output_tokens": 1600, "store": False,
               "include": ["reasoning.encrypted_content"]}
    request = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(),
                      headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                               "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise Problem(502, "PROVIDER_RESPONSE_TOO_LARGE", "模型回應超過大小上限")
        result = json.loads(data)
    except HTTPError as error:
        # Never expose provider bodies, which can include user data or credentials.
        code = "PROVIDER_RATE_LIMIT" if error.code == 429 else "PROVIDER_ERROR"
        raise Problem(502, code, "OpenAI 請求失敗，請檢查後端模型設定、額度與權限") from None
    except (TimeoutError, socket.timeout):
        raise Problem(504, "PROVIDER_TIMEOUT", "OpenAI 請求逾時，未儲存複習計畫") from None
    except (URLError, OSError):
        raise Problem(502, "PROVIDER_UNAVAILABLE", "無法連線至 OpenAI") from None
    except (ValueError, UnicodeError):
        raise Problem(502, "PROVIDER_INVALID_RESPONSE", "OpenAI 未回傳有效 JSON") from None
    if not isinstance(result, dict) or result.get("status") != "completed" or not isinstance(result.get("output"), list):
        raise Problem(502, "PROVIDER_INCOMPLETE", "模型未完成本回合，未採用不完整結果")
    return result
