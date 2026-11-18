# Week 09 — Optimization：智慧學習 Context Optimization

## 本週做什麼

延續原「學生個人安排系統」與「智慧學習／讀書時段」功能，不新增另一套 Demo。

本週只改 **Study Load Review Expert 的 context**，採用課堂允許的 **Few-shot Prompting**：

- Baseline：`week08-instruction-v1`
- Candidate：`week09-few-shot-v1`
- 模型權重不變
- deterministic scheduler 不變
- Tool 不變
- 權限不變
- 前後端入口不變

Baseline SHA：`cf7376f97c6a85129c796580957df589512e2ef2`

## 改動位置

### Backend provider

`backend/app/study_agent_openai.py`

Candidate 在原 Study Load Review Expert 指令後加入三個 few-shot：

1. `remainingMinutes > 0` → `insufficient`
2. 全部時數已排滿，但單日占三分之二以上 → `concentrated`
3. 已排滿且分散 → `balanced`

Baseline 保留 Week 08 原指令，不放這些示範。

### 固定評估

`backend/app/study_agent_api.py`

同一個 deterministic plan 用固定 rubric 評分：

- remainingMinutes > 0 → insufficient
- remainingMinutes = 0 且任一日期分鐘數占總 scheduledMinutes 至少 2/3 → concentrated
- 其他 → balanced

比較指標：

`assessment exact match against deterministic rubric`

因此選版不是靠「看起來比較好」，而是同案例、同 plan、同模型、同 metric。

## 主流程

原入口仍是：

```text
React 智慧學習
→ POST /api/v1/study-agent/run
→ Flask
→ Coordinator tool selection
→ deterministic planner
→ Study Load Review Expert（Week 09 Candidate context）
→ Coordinator final summary
→ React
```

主流程回傳新增：

```json
{
  "optimization": {
    "week": 9,
    "method": "few-shot prompting",
    "baselineContextVersion": "week08-instruction-v1",
    "candidateContextVersion": "week09-few-shot-v1",
    "metric": "assessment exact match against deterministic rubric"
  }
}
```

## 同一案例兩版比較

新增後端：

```text
POST /api/v1/study-agent/context-comparison
```

它會：

1. 驗證一次 request。
2. 建立一次 deterministic plan。
3. 對完全相同的 expert packet 跑 Baseline。
4. 對完全相同的 expert packet 跑 Candidate。
5. 用相同固定 rubric 分別評分。
6. 回傳兩版 output、context version、usage、PASS/FAIL、observation、run ID。

不寫入 SQLite，也不重排兩次。

## Frontend

`frontend/src/components/StudyPlanner.jsx`

在原「智慧學習」頁新增 **Week 09 上下文優化**區塊。

先成功跑一次主流程後，可按：

**用同一案例比較 Baseline / Candidate**

畫面會顯示：

- expected assessment
- Baseline context version／實際 assessment／PASS or FAIL
- Candidate context version／實際 assessment／PASS or FAIL
- observation
- comparison run ID

這是 Flask API 真正回傳的結果，不是前端硬編結果。

## 離線驗證

```bash
python -m pytest backend/tests/test_study_agent_service.py backend/tests/test_study_agent_openai.py -q
python -m week09.run_acceptance

cd frontend
npm test
npm run build
npm run format:check
```

`week09.run_acceptance` 使用明確標示的 `OFFLINE_INJECTED` provider，只驗證「兩版同案例比較管線＋固定 evaluator」；它**不能**拿來宣稱真實模型改善。

## 真實比較

GitHub CI 沒有私人 `OPENAI_API_KEY`，因此目前 Week 09 真實模型狀態維持 `LIVE_NOT_RUN`。

在本機 server-side key 已設定時：

1. 啟 Flask。
2. 啟 React。
3. 進智慧學習，先跑主流程。
4. 點「用同一案例比較 Baseline / Candidate」。
5. 保存畫面中的兩版 output、run ID、context version 與觀察。

只有真實 provider 兩版都實際執行後，才能把 Live 改成 `LIVE_PASS`。

## 觀察原則

- Baseline FAIL、Candidate PASS：支持這一案例改善。
- 兩版都 PASS：這一案例尚不足以證明 Candidate 更好。
- Candidate FAIL：不採用。
- 單一案例永遠不足以證明整體性能提升；這週先完成課堂要求的同案例兩版比較。

## 交付

- `backend/app/study_agent_openai.py`
- `backend/app/study_agent_api.py`
- `frontend/src/lib/studyAgentClient.js`
- `frontend/src/components/StudyPlanner.jsx`
- `backend/tests/test_study_agent_service.py`
- `backend/tests/test_study_agent_openai.py`
- `frontend/tests/studyAgentClient.test.js`
- `week09/run_acceptance.py`
- `week09/evidence/offline_comparison.json`（CI 產生）
- `week09/evidence/LIVE_NOT_RUN.json`
- `docs/week09/SHORT_RECORD.md`


## GitHub Actions 實測

Verified implementation SHA：`be1afdac6f61f6a1ec00c6890f75b0013bdba0b3`

- Week 09 run：`44216456067`
- Job：`134507385419`
- Backend focused：15 passed
- Offline comparison：`offline_all_pass=true`
- Frontend：41 / 41 passed
- Vite production build：PASS
- Prettier：PASS
- Artifact：`14388587457`

同一 candidate 也重新跑 Week 08 regression workflow：

- Run：`44216456091`
- Job：`134507386238`
- Result：PASS

### 私有環境真實兩版比較

```bash
python -m week09.live_compare
```

需要 server-side `OPENAI_API_KEY`。Runner 不會把 key 寫入 evidence。
