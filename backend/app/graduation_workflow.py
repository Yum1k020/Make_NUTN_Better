"""Read-only graduation planning orchestration; business rules stay in the app."""

from typing import TypedDict
from flask import current_app
from langgraph.graph import START, END, StateGraph
from .planner_graduation import (
    load_graduation_context, collect_graduation_credits,
    allocate_graduation_credits, evaluate_graduation_requirements,
    finish_graduation_progress,
)


class GraduationState(TypedDict, total=False):
    result: dict
    rule: dict | None
    document: dict
    rule_id: str
    passed: set[str]
    unknown: bool
    groups: dict
    earned: float
    totals: dict


def progress_graph(db):
    def event(name):
        current_app.logger.info("graduation workflow: %s", name,
                                extra={"workflow_node": name})

    def load(state):
        event("load_rules")
        return load_graduation_context(db)

    def route(state):
        return "collect" if state["rule"] is not None else "unavailable"

    def unavailable(state):
        event("unavailable")
        return {"result": state["result"]}

    def collect(state):
        event("collect")
        return collect_graduation_credits(db, state)

    def allocate(state):
        event("allocate")
        return allocate_graduation_credits(state)

    def evaluate(state):
        event("evaluate")
        return evaluate_graduation_requirements(db, state)

    def summarize(state):
        event("summarize")
        return {"result": finish_graduation_progress(state)}

    graph = StateGraph(GraduationState)
    for name, node in (("load_rules", load), ("unavailable", unavailable),
                       ("collect", collect), ("allocate", allocate),
                       ("evaluate", evaluate), ("summarize", summarize)):
        graph.add_node(name, node)
    graph.add_edge(START, "load_rules")
    graph.add_conditional_edges("load_rules", route,
                                {"collect": "collect", "unavailable": "unavailable"})
    for a, b in (("collect", "allocate"), ("allocate", "evaluate"),
                 ("evaluate", "summarize"), ("summarize", END), ("unavailable", END)):
        graph.add_edge(a, b)
    # Synchronous execution keeps the existing request-scoped SQLite transaction.
    result = None
    for update in graph.compile().stream({}, config={"recursion_limit": 8}, stream_mode="updates"):
        for node in ("summarize", "unavailable"):
            if node in update:
                result = update[node]["result"]
    if result is None:
        raise ValueError("Graduation workflow did not produce a result")
    return result
