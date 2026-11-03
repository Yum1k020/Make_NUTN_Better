# Week 06 — 兩條可驗證的 Agent Workflow

整合後的專案保留兩條互不取代的 Week 06 子流程。兩者都把模型限制在明確資料契約內，讓一般程式負責可重現的計算與安全檢查。

| 子流程 | 使用者目標 | 模型責任 | 一般程式責任 | 主要入口 |
| --- | --- | --- | --- | --- |
| 智慧學習 | 依課程、私人行程與考試需求安排複習 | 擷取結構化需求、整理已驗證排程 | 規則排程、衝突與完整性 Gate、停止條件 | `backend/week06_chaining.py`、`frontend/server/studyPlanWorkflow.js` |
| 畢業進度 | 將畢業缺項整理成可核對的說明 | 產生結構化說明，依評估錯誤最多修正一次 | 學分與條件計算、來源核對、同規準評估、回退 | `backend/app/graduation_explanation_api.py`、`backend/app/graduation_explanation_core.py` |

## 智慧學習 Prompt Chaining

```text
需求驗證
  -> 確定性規則排程
  -> 衝突與完整性 Gate
  -> 模型說明
```

- `INVALID_REQUEST`：輸入不合法，不執行排程或模型。
- `RULE_ENGINE_FAILED`：規則排程失敗，不進入 Gate。
- `PLAN_GATE_REJECTED`：Gate 拒絕，模型呼叫數必須為 0。
- `AGENT_STAGE_FAILED`：模型說明失敗，仍保留規則排程。

Python 課堂驗收與網站整合目前都使用伺服器端 OpenAI。兩者都以規則排程為唯一時段結果來源。詳見 [`adr-001-study-plan-prompt-chaining.md`](adr-001-study-plan-prompt-chaining.md)、[`COMPARISON.md`](COMPARISON.md) 與 [`EVIDENCE_INDEX.md`](EVIDENCE_INDEX.md)。

## 畢業缺項 Evaluator–optimizer

```text
讀取目前使用者與規則
  -> 一般程式計算畢業進度
  -> OpenAI 產生結構化說明 A
  -> 固定規準評估
  -> 未通過時產生 B，使用同一規準重評
  -> 通過則顯示；否則回退基本進度
```

模型只取得去識別的彙整檢查，不取得姓名、學號、逐筆成績、登入憑證或寫入工具。每次操作最多兩次模型請求，provider 失敗或第二稿仍不合格時有限停止。`GET /api/v1/graduation-progress` 保持零模型呼叫；使用者明確按下按鈕才呼叫 `POST /api/v1/graduation-explanation`。

完整契約、執行方式與限制見 [`GRADUATION_EXPLANATION.md`](GRADUATION_EXPLANATION.md)、[`contract.md`](contract.md) 與 [`comparison.md`](comparison.md)。歷史 `evidence/live.json` 為 `LIVE_NOT_RUN`，不可把 fixture 當成真實 OpenAI。

## 本機驗證

```bash
./.venv/bin/python -m pytest
./.venv/bin/python scripts/verify_environment.py

cd frontend
npm test
npm run build
npm run format:check
```

需要真實 provider 的測試必須另行執行並標示 `LIVE_NOT_RUN`、`LIVE_FAIL` 或 `LIVE_PASS`。不得提交 `.env`、API key、token 或個人資料。
