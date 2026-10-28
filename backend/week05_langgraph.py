from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.week04_tools import preview_study_plan, save_study_plan


class StudyPlanGraphState(TypedDict, total=False):
    request: dict[str, Any]
    request_id: str
    preview: dict[str, Any]
    confirmation: str
    save_result: dict[str, Any]
    status: str


def _preview_node(state: StudyPlanGraphState) -> StudyPlanGraphState:
    preview = preview_study_plan(**state["request"])
    return {
        "preview": preview,
        "status": "awaiting_confirmation",
    }


def _approval_node(state: StudyPlanGraphState) -> Command:
    preview = state["preview"]
    decision = interrupt(
        {
            "action": "save_study_plan",
            "question": "確認寫入這份複習排程？只有 YES 才執行。",
            "request_id": state["request_id"],
            "plan_id": preview["plan_id"],
            "scheduled_minutes": preview["scheduled_minutes"],
            "session_count": len(preview["suggested_sessions"]),
        }
    )
    accepted = str(decision).strip() == "YES"
    return Command(
        update={"confirmation": str(decision)},
        goto="save" if accepted else "reject",
    )


def _save_node_factory(store_path: Path):
    def _save_node(state: StudyPlanGraphState) -> StudyPlanGraphState:
        result = save_study_plan(
            preview=state["preview"],
            confirmed=True,
            request_id=state["request_id"],
            store_path=store_path,
        )
        return {
            "save_result": result,
            "status": "saved" if result["executed"] else result["status"],
        }

    return _save_node


def _reject_node_factory(store_path: Path):
    def _reject_node(state: StudyPlanGraphState) -> StudyPlanGraphState:
        result = save_study_plan(
            preview=state["preview"],
            confirmed=False,
            request_id=state["request_id"],
            store_path=store_path,
        )
        return {
            "save_result": result,
            "status": "rejected",
        }

    return _reject_node


class StudyPlanLangGraphRuntime:
    """Week 05 candidate orchestration around the existing Week 04 tools.

    LangGraph takes over pause/resume and checkpointing only. Scheduling rules,
    exact confirmation semantics, persistence, and idempotency stay in the
    existing application tools.
    """

    def __init__(self, *, checkpoint_path: str | Path, store_path: str | Path):
        self.checkpoint_path = Path(checkpoint_path)
        self.store_path = Path(store_path)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(
            self.checkpoint_path,
            check_same_thread=False,
        )
        self._checkpointer = SqliteSaver(self._connection)

        builder = StateGraph(StudyPlanGraphState)
        builder.add_node("preview", _preview_node)
        builder.add_node("approval", _approval_node)
        builder.add_node("save", _save_node_factory(self.store_path))
        builder.add_node("reject", _reject_node_factory(self.store_path))
        builder.add_edge(START, "preview")
        builder.add_edge("preview", "approval")
        builder.add_edge("save", END)
        builder.add_edge("reject", END)
        self.graph = builder.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _config(thread_id: str) -> dict[str, Any]:
        if not thread_id.strip():
            raise ValueError("thread_id is required")
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _normalize(result: dict[str, Any]) -> dict[str, Any]:
        output = {key: value for key, value in result.items() if key != "__interrupt__"}
        interrupts = result.get("__interrupt__", ())
        if interrupts:
            output["interrupts"] = [
                {
                    "id": getattr(item, "id", None),
                    "value": getattr(item, "value", None),
                }
                for item in interrupts
            ]
        return output

    def start(
        self,
        *,
        request: dict[str, Any],
        request_id: str,
        thread_id: str,
    ) -> dict[str, Any]:
        if not request_id.strip():
            raise ValueError("request_id is required")
        result = self.graph.invoke(
            {
                "request": request,
                "request_id": request_id,
                "status": "started",
            },
            config=self._config(thread_id),
        )
        return self._normalize(result)

    def resume(self, *, thread_id: str, decision: str) -> dict[str, Any]:
        result = self.graph.invoke(
            Command(resume=decision),
            config=self._config(thread_id),
        )
        return self._normalize(result)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "StudyPlanLangGraphRuntime":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
