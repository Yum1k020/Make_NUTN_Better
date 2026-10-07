from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.week03_retrieval import load_graduation_chunks, trace_query

RULES = ROOT / "backend" / "app" / "data" / "nutn_csie_115_graduation_rules_v1.json"
QUERIES = ROOT / "week03" / "fixed_queries.json"
OUT = ROOT / "week03" / "evidence" / "retrieval_trace.json"


def main() -> None:
    chunks = load_graduation_chunks(RULES)
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))
    traces = [
        trace_query(
            query_id=item["query_id"],
            query=item["query"],
            chunks=chunks,
            top_k=3,
        )
        for item in queries
    ]
    artifact = {
        "source": str(RULES.relative_to(ROOT)),
        "index_version": "week03-transparent-v1",
        "retriever": "character_bigram_plus_domain_boost",
        "traces": traces,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
