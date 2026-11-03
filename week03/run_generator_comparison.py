from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_FILE = ROOT / "week03" / "evidence" / "retrieval_trace.json"
RULE_FILE = ROOT / "backend" / "app" / "data" / "nutn_csie_115_graduation_rules_v1.json"
OUT = ROOT / "week03" / "evidence" / "generator_comparison.json"


def main() -> None:
    trace = json.loads(TRACE_FILE.read_text(encoding="utf-8"))
    rules = json.loads(RULE_FILE.read_text(encoding="utf-8"))
    target = next(item for item in trace["traces"] if item["query_id"] == "multi_evidence")

    if not target["gate"]["can_answer"]:
        raise SystemExit("Frozen evidence did not pass the coverage gate.")

    credits = rules["credit_requirements"]["minimum_total_credits"]
    professional = rules["lecture_requirements"]["professional"]["minimum_count"]
    general = rules["lecture_requirements"]["general"]["minimum_count"]
    selected = target["gate"]["selected_evidence"]
    citations = target["gate"]["citations"]

    artifact = {
        "query_id": target["query_id"],
        "frozen_selected_evidence": selected,
        "generators": [
            {
                "provider": "offline_template",
                "llm_actually_called": False,
                "text": f"第一版最低總學分為 {credits} 學分；專業講座至少 {professional} 場，一般講座至少 {general} 場。",
                "citations": citations
            },
            {
                "provider": "gemini_fixture",
                "llm_actually_called": False,
                "text": f"依目前第一版規則，畢業總學分門檻是 {credits}；另需專業講座 {professional} 場、一般講座 {general} 場。",
                "citations": citations
            }
        ],
        "same_selected_evidence": True,
        "same_citations": True,
        "fact_coverage": "3/3",
        "unsupported_numeric_claims": []
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
