# Week 02 — Baseline Declaration

## User Story

身為大學生，我希望系統依照考試日期、需要複習的分鐘數、可安排時段與既有課表／私人行程，
產生不衝突的複習計畫，讓我能提早安排讀書。

## Scope

本週只做固定資料下的「複習排程預覽」：

- deterministic scheduler
- 固定 request / response contract
- 固定 fixture
- 200 / 422 / 502 三個驗收案例
- pytest 可重現

## Out of Scope

- 不直接寫正式資料庫
- 不直接寫 Google Calendar
- 不做完整 Agent architecture
- 不把 fixture 當作真實 LLM 能力證據

## I/O Contract

### Request

- `plan_id`
- `start_date`
- `exam_date`
- `target_minutes`
- `session_minutes`
- `allowed_windows`
- `busy_intervals`

### Response

- `plan_id`
- `suggested_sessions`
- `scheduled_minutes`
- `remaining_minutes`
- `reason`

## Acceptance Cases

### 200

Given：輸入完整，而且考試前有足夠空閒時間。  
When：POST `/api/study-plan`。  
Then：HTTP 200；排程避開 busy intervals；已安排分鐘數符合需求。

### 422

Given：缺少必要欄位或日期／分鐘不合法。  
When：POST `/api/study-plan`。  
Then：HTTP 422；scheduler 不產生可用結果。

### 502

Given：request 合法。  
When：排程後方的 generation / upstream boundary 發生 RuntimeError。  
Then：HTTP 502，回傳 `UPSTREAM_GENERATION_UNAVAILABLE`。

## Baseline Type

`deterministic fixture-backed baseline`

理由：先固定資料、輸入／輸出與停止層，讓後續 Week 03 的 retrieval 與 Week 04 的 tool use
都可以跟同一個排程核心比較。

## Known Failure

固定案例：

- allowed window：09:00–10:30
- target：120 分鐘
- session：60 分鐘

目前 v1 只排 09:00–10:00；10:00–10:30 的 30 分鐘尾段不會自動建立 partial session，因此只排 60 分鐘、剩 60 分鐘。理想的後續版本可再利用該 30 分鐘，變成已排 90、剩 30。
此案例保留為 `xfail`，後續若決定支援可再修正。

## Reproduction

```powershell
py -m uvicorn backend.week02_api:app --reload
py -m pytest -c pytest_agentic.ini -v
```
