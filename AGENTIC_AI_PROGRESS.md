# Agentic AI Engineering — Weeks 02–04 Project Evidence

這份資料是 **C／智慧排程** 的跨週累積，不覆蓋組員既有的：

- `README.md`
- `DATA_GUIDE.md`
- `frontend/`
- `backend/app/data/nutn_csie_115_graduation_rules_v1.json`

而是把 Week 02 → Week 03 → Week 04 串成同一條工程證據鏈。

## Week 02 — Reliable Interface / Baseline

核心：

```text
固定 request
  ↓
POST /api/study-plan
  ↓
deterministic scheduler
  ↓
固定 response
```

證據：

- request / response contract
- HTTP 200 / 422 / 502
- deterministic fixture
- known failure (`xfail`)
- `week02/BASELINE_DECLARATION.md`

## Week 03 — RAG / Evidence Gate

選定 claim：

> 115 學年度入學的資工系學生，第一版畢業最低總學分是多少？

資料來源：

```text
backend/app/data/nutn_csie_115_graduation_rules_v1.json
```

流程：

```text
fixed query
  ↓
transparent retrieval baseline
  ↓
top-k trace
  ↓
evidence coverage gate
  ↓
answer / abstain
```

證據：

- proposal
- source card
- normal / paraphrase / no-answer
- multi-evidence coverage
- retrieval trace JSON
- generator comparison JSON

## Week 04 — Tool Use / MCP

同一專題的「一讀一寫」：

```text
READ  preview_study_plan
      只產生排程，不修改資料

WRITE save_study_plan
      使用者確認後才寫本機合成資料
      request_id 防止重複寫入
```

另外提供：

- MCP read-only tool
- tools/list + tools/call trace
- Gemini → tool → functionResponse → Gemini runner
- Action Readiness
- Self Check

## 跨週關係

```text
Week 02
可驗證 API / Baseline
        ↓
Week 03
外部 evidence / retrieval / gate
        ↓
Week 04
模型提案 / tool validation / human approval / execution / audit
```

每週新增能力，但保留前一週的可重現證據。
