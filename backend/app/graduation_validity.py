"""Week 07 C: bounded lifetime for derived explanations, no academic-data writes."""
from hashlib import sha256
from time import time
from uuid import uuid4
from flask import current_app, session
from .planner_core import dump

TTL_SECONDS = 300

def clock_ms():
    clock = current_app.config.get("GRADUATION_CLOCK", time) if current_app.testing else time
    return int(clock() * 1000)

def source_digest(result, rule_digest):
    stable = {k: v for k, v in result.items() if k != "evaluated_at"}
    return sha256(dump({"progress": stable, "rule_digest": rule_digest}).encode()).hexdigest()

def context(result, rule_digest):
    if "graduation_scope" not in session:
        session["graduation_scope"] = str(uuid4())
    return {"scope_id": session["graduation_scope"],
            "source_sha256": source_digest(result, rule_digest), "server_now_ms": clock_ms(),
            "execution_mode": "synthetic_fixture" if current_app.testing and current_app.config.get("GRADUATION_FIXTURE_ONLY") else "standard"}

def lease(current):
    return {**current, "issued_at_ms": current["server_now_ms"],
            "expires_at_ms": current["server_now_ms"] + TTL_SECONDS * 1000,
            "ttl_seconds": TTL_SECONDS}

def current_rule_digest(db, rule_id):
    row = db.execute("SELECT digest FROM graduation_rule_documents WHERE rule_set_id=?", (rule_id,)).fetchone()
    return row["digest"] if row else None
