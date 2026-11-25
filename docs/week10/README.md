# Week 10：智慧學習主流程可重現驗證

整理日期：2026-11-25

## 本週範圍

Week 10 課堂不指定新功能、資料包或提交增量，自主實作的完成標準是確認一條主要流程能從輸入跑到可核對結果。本專案選定「智慧學習排程」，只處理前後端課表來源不一致與示範日期過期這一個問題。

## 問題與修正

修正前，React 畫面顯示 Flask／SQLite 載入的課表，但 Agent 後端排程仍使用程式內寫死的課表；畫面與 Agent 可能因此對「哪些時段有衝突」得到不同結果。示範起始日與考試日也固定在 2026-09-17 與 2026-09-24，不適合 11 月以後的課堂示範。

修正後：

- 前端將目前載入的 `weeklyClasses` 與規劃需求一起送到 Flask。
- Flask 嚴格驗證課表欄位、時間與筆數，並把同一份課表用於確定性排程與結果 Gate。
- OpenAI 工具參數 schema 也必須包含 `weeklyClasses`；模型改寫任一參數時仍在執行工具前停止。
- 示範起始日使用本機當日，預設考試日為七天後，並使用本地日期而非 UTC 切日。

## 可重現主流程

1. 前端建立課名、日期、需要時數、單次時長、允許時段、課表與私人行程的請求。
2. Flask 完成 schema 驗證後，要求 OpenAI 呼叫 `get_validated_study_plan`。
3. 後端比對模型工具參數與原請求，完全一致才執行確定性排程。
4. 排程器避開課表、私人行程與已建立的複習時段，Gate 再重新核對日期、時段、衝突與總分鐘數。
5. 工具結果回送模型產生結構化說明；前端另以同一請求計算規則結果，只在兩者一致時顯示 Agent 完成。

## 驗證與界線

- `backend/tests/test_study_agent_service.py` 證明同一請求在有、無週課表時會產生不同的第一個可用時段，並驗證完整 function-call 流程、參數 Gate 與 HTTP 邊界。
- `frontend/tests/studyAgentClient.test.js` 檢查送出的 JSON 包含去除 UI 欄位後的課表，且不包含 API key。
- 所有示範資料仍是合成資料，不是即時校務資料。本週沒有新增登入、多使用者授權或正式部署。

2026-11-25 本機驗證結果：

- 整合 Week 8、9 遠端更新後，後端完整回歸：331 passed、5 skipped。
- 整合 Week 8、9 遠端更新後，前端測試：41 passed；Vite production build 與 Prettier 檢查通過。
- OpenAI 合成資料 smoke test 已實際送出，但回傳 `OPENAI_HTTP_401`，因此當次結論是 `LIVE_FAIL`，不是 `LIVE_PASS`。清理後紀錄位於 [`evidence/study-agent-openai-live.json`](evidence/study-agent-openai-live.json)；檔案不含憑證、token、原始回應或個人資料。
- 若要完成真實模型驗收，需先在本機 `.env.local` 改用可授權的 `OPENAI_API_KEY`，再重跑 `backend/midterm_live.py --output docs/week10/evidence/study-agent-openai-live.json`。


## Agent Data Package 增量

在同學已完成的「前後端課表來源一致化」上，本週再把課堂的 Task / Environment / Trajectory / Verifier 概念接回同一條智慧學習主流程；沒有另建第二份 demo 資料。

### 資料流

```text
App.jsx
  ├─ Flask/SQLite academic.weeklyClasses
  ├─ Flask/SQLite personalEvents
  └─ 已整合 study planner state
          ↓
StudyPlanner.jsx
          ↓
POST /api/v1/study-agent/run
          ↓
Coordinator → deterministic planner → Expert → Coordinator
          ↓
verify_plan + expert assessment rubric
          ↓
dataPackage
          ↓
React「Week 10 Agent Data Package」
```

### Data Package 結構

- **Task**：課程、日期範圍、目標分鐘、單次分鐘、允許時段。
- **Environment**：
  - 課表來源標示 `flask-sqlite:academic-timetable`。
  - 私人行程來源標示 `flask-sqlite:personal-events`。
  - 私人行程只保留 id / date / start / end，title / location 不進可重用資料包。
- **Trajectory**：把既有 Week 08 / 09 workflow stages 轉成 step / actor / action / status。
- **Verifier**：沿用 `verify_plan` 與固定 study-load rubric，不讓模型自我宣告成功。
- **Provenance**：標示整合同學資料、排除 credentials 與私人行程文字。

### 來源標籤修正

先前 structured output 仍允許 `weekly-classes-fixture`，但目前課表已由 Flask／SQLite academic state 提供，因此更新為：

`weekly-classes-backend-sqlite`

### 前端

Agent 成功後會直接顯示「Week 10 Agent Data Package」，包含環境資料筆數、完整 trajectory、verifier 結果與 package ID。

### 驗收

```bash
python -m pytest backend/tests/test_study_agent_service.py backend/tests/test_study_agent_openai.py -q
python -m week10.run_acceptance

cd frontend
npm test
npm run build
npm run format:check
```

`week10.run_acceptance` 使用 `OFFLINE_INJECTED` provider，只驗證資料整合、redaction、trajectory 與 deterministic verifier；不冒充真實模型成功。


## GitHub Actions 實測（Agent Data Package）

Verified implementation SHA：`ebc1e604e56d5402c14e7d2a4023159539cf3e1d`

- Week 10 run：`45530040876`
- Week 10 job：`138922775744`
- Focused backend：17 passed
- Offline acceptance：`offline_all_pass=true`
- Frontend：41 / 41 passed
- Vite production build：PASS
- Prettier：PASS
- Artifact：`14984596003`

同一 candidate 也重新跑既有回歸：

- Week 09 run：`45530040897` → PASS
- Week 08 run：`45530040946` → PASS

實際 CI 產生的離線資料包已提交到 `week10/evidence/offline_data_package.json`。它標示為 `OFFLINE_INJECTED`，用來證明資料來源、redaction、trajectory 與 verifier 管線，不代表真實模型訓練資料品質已被驗證。
