from pathlib import Path

from backend.week03_retrieval import load_graduation_chunks, trace_query

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "backend" / "app" / "data" / "nutn_csie_115_graduation_rules_v1.json"


def chunks():
    return load_graduation_chunks(RULES)


def test_week03_normal_query_finds_total_credits():
    trace = trace_query("normal", "115資工系畢業至少要幾學分？", chunks())
    assert trace["gate"]["can_answer"] is True
    assert "grad-total-credits" in trace["gate"]["selected_evidence"]


def test_week03_paraphrase_still_finds_total_credits():
    trace = trace_query(
        "paraphrase",
        "115學年度入學的資工大學部，第一版總學分門檻是多少？",
        chunks(),
    )
    assert trace["gate"]["can_answer"] is True
    assert "grad-total-credits" in trace["gate"]["selected_evidence"]


def test_week03_no_answer_abstains():
    trace = trace_query(
        "no_answer",
        "明天資料庫系統在哪一間教室上課？",
        chunks(),
    )
    assert trace["gate"]["can_answer"] is False
    assert trace["gate"]["failure_code"] == "INSUFFICIENT_EVIDENCE"
    assert trace["gate"]["citations"] == []


def test_week03_multi_evidence_coverage():
    trace = trace_query(
        "multi_evidence",
        "第一版畢業總學分是多少？專業講座和一般講座各要幾場？",
        chunks(),
    )
    assert trace["gate"]["can_answer"] is True
    assert "grad-total-credits" in trace["gate"]["selected_evidence"]
    assert "grad-lecture-counts" in trace["gate"]["selected_evidence"]
    assert trace["gate"]["coverage"]["missing"] == []
