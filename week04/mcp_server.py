from pathlib import Path
from mcp.server import MCPServer

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_GUIDE = REPO_ROOT / "DATA_GUIDE.md"

mcp = MCPServer(
    "NUTN Student Planner Read Tools",
    instructions="Read only the approved project data contract. Never write project files.",
)


def _extract(start_heading: str, next_heading: str) -> str:
    if not DATA_GUIDE.exists():
        raise FileNotFoundError("DATA_GUIDE.md not found in repo root")
    text = DATA_GUIDE.read_text(encoding="utf-8")
    start = text.find(start_heading)
    if start < 0:
        raise ValueError(f"section not found: {start_heading}")
    end = text.find(next_heading, start + len(start_heading))
    if end < 0:
        end = len(text)
    return text[start:end].strip()


@mcp.tool()
def read_study_plan_contract(section: str) -> dict:
    """Read an approved section of DATA_GUIDE.md. Read-only."""
    allowed = {
        "study_plans": ("### 4.8 複習計畫", "### 4.9 修課規劃"),
        "module_handoff": ("## 8. AI 與計算模組的交接", "## 9. 關聯與單一資料來源"),
    }
    if section not in allowed:
        raise ValueError("section must be study_plans or module_handoff")
    start, end = allowed[section]
    return {
        "section": section,
        "source": "DATA_GUIDE.md",
        "content": _extract(start, end),
        "mutated": False,
    }


if __name__ == "__main__":
    mcp.run()
