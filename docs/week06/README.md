# Week 06 — Prompt Chaining Workflow

## 一句話交付

「智慧學習」的規劃子流程使用 Prompt chaining，將需求驗證、確定性排程、衝突與完整性 Gate、模型說明分成可檢查的階段。Gate 拒絕後必須有限停止，不可再呼叫下游模型。

## 整合後的兩個執行面

合併歷史保留了兩個使用相同控制邊界的實作：

| 執行面 | 用途 | 主要入口 | Provider |
| --- | --- | --- | --- |
| Python 課堂驗收 | 離線比較、Gemini live runner 與 CI 證據 | `backend/week06_chaining.py`、`week06/live_chaining.py` | Gemini |
| React 網站 | 使用者觸發規劃時顯示四階段 trace | `frontend/server/studyPlanWorkflow.js`、`frontend/src/components/StudyPlanner.jsx` | OpenAI Agents SDK |

兩邊都保留原本的規則排程為真正結果來源；模型只做結構化抽取或說明，不得跳過 Gate 修改排程。

## 固定 Workflow

```text
需求驗證
  -> 確定性規則排程
  -> 衝突與完整性 Gate
  -> 模型說明
```

| 階段 | 放行條件 | 失敗後續 |
| --- | --- | --- |
| 需求驗證 | 日期、時數、時段與輸入 schema 合法 | 不執行排程與 Agent |
| 規則排程 | 回傳 sessions、scheduledMinutes、remainingMinutes | 不進入 Gate |
| 安全 Gate | 日期、時段、衝突、時數與 ID 均通過 | 不呼叫 Agent |
| 模型說明 | Provider 成功且輸出符合 schema | 保留原規則排程與錯誤說明 |

## 公開停止狀態

- `INVALID_REQUEST`：需求驗證失敗。
- `RULE_ENGINE_FAILED`：規則排程失敗。
- `PLAN_GATE_REJECTED`：Gate 拒絕，Agent 呼叫數必須為 0。
- `AGENT_STAGE_FAILED`：模型說明失敗，當次規則結果仍可使用。

Trace 只保留階段、狀態、計數、公開 stop reason 與 run ID，不保存 API key、完整 prompt、私人行程內容或模型內部推理。

## 程式與驗證

- `backend/week06_chaining.py`：Python workflow 與 Gate。
- `week06/gemini_client.py`：Gemini extraction 與 summary client。
- `frontend/server/studyPlanWorkflow.js`：網站四階段 workflow。
- `frontend/server/studyAgent.js`：Gate 通過後才呼叫 Agents SDK。
- `frontend/src/components/StudyPlanner.jsx`：顯示階段、結果、stop reason 與 run ID。
- `tests/test_week06_chaining.py` 與 `frontend/tests/studyPlanWorkflow.test.js`：正常、非法輸入、provider 失敗與 Gate 邊界。

```bash
./.venv/bin/python -m pytest
./.venv/bin/python scripts/verify_environment.py

cd frontend
npm test
npm run build
npm run format:check
```

Python 離線比較已驗證 `offline_all_pass=true`；網站的真實 provider 需在本機安全設定 `OPENAI_API_KEY` 後另行執行。CI 沒有私人 key 時，不得將 fixture 宣稱為 live pass。
