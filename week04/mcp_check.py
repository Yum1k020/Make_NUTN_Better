import anyio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
SERVER = HERE / "mcp_server.py"
EVIDENCE = HERE / "evidence" / "mcp_read_trace.json"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    trace = {
        "run_id": datetime.now(timezone.utc).strftime("MCP-%Y%m%dT%H%M%SZ"),
        "transport": "stdio",
        "expected_protocol": "2026-07-28",
    }
    async with Client(params, mode="auto") as client:
        listed = await client.list_tools()
        names = [tool.name for tool in listed.tools]
        trace["protocol_version"] = str(client.protocol_version)
        trace["tools_list"] = names
        if "read_study_plan_contract" not in names:
            raise RuntimeError("read_study_plan_contract not discovered")
        result = await client.call_tool(
            "read_study_plan_contract",
            {"section": "study_plans"},
        )
        trace["tools_call"] = {
            "name": "read_study_plan_contract",
            "arguments": {"section": "study_plans"},
            "structured_content": result.structured_content,
        }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(trace, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    anyio.run(main)
