# 第 3–7 週課程概念與專案實作對照

整理日期：2026-11-03

本文件回答「專案哪些部分使用了老師上課教到的內容」。判定依據同時包含課堂投影片、目前程式、測試與網站接線狀態。

## 狀態定義

| 狀態 | 意義 |
| --- | --- |
| 網站已接入 | 目前 Vite／Flask 示範流程可直接操作 |
| 獨立實作 | 有可執行程式與測試，但不是目前網站主流程的一部分 |
| 部分實作 | 有課堂概念的 scaffold 或固定資料驗證，未完成完整技術管線 |
| 未實作 | 目前程式與執行證據不足，不應在報告中宣稱完成 |

## 總表

| 週次與課堂重點 | 專案對應 | 證據入口 | 判定與報告界線 |
| --- | --- | --- | --- |
| Week 03 RAG：source card、fixed queries、top-k trace、evidence gate、citation、no-answer（投影片 5、12–13、24） | 「資料證據」頁面保存來源權威性／權限／時效；以 3 個固定查詢顯示 top-k、selected evidence、citation audit 及即時停課問題的拒答 | `frontend/src/components/GateEvidence.jsx`、`frontend/src/data/evidence.js`、`frontend/src/lib/evidence.js`、`frontend/tests/planner.test.js` | **部分實作。** 目前 top-k 與分數是固定 fixture，沒有 embedding、vector store、BM25／hybrid retrieval 或正式 ingestion。可稱「RAG evidence-gate prototype」，不可稱完整 production RAG。 |
| Week 04 Tool Use：模型提出 function call、Host 驗 schema／語意、工具執行、function response 回模型；寫入需人工確認與防重送（投影片 6、8、11–16） | Gemini／OpenAI adapter 只允許 `get_validated_study_plan`；後端重驗模型參數必須等於原需求，執行確定性排程，再把結果回模型。`save_study_plan` 另有 `confirmed` 與 `request_id` 冪等控制 | `backend/app/study_agent_api.py`、`backend/app/study_agent_vertex.py`、`backend/week04_tools.py`、`backend/tests/test_study_agent_vertex.py`、`tests/test_week04_tools.py` | 唯讀工具為**網站已接入**；寫入工具為**獨立實作**，尚未接到目前網站主畫面，也沒有由主流程模型在兩個工具間選擇。 |
| Week 04 MCP：Host 透過 MCP client/server 發現及呼叫外部能力（投影片 25–39） | 目前工具是同一專案內的直接 Function Calling；沒有 `tools/list`、MCP transport 或 MCP server | 無 | **未實作。** 報告應說明工具數量少且只供單一應用，所以目前選擇直接串接；不能把一般 `/api` 或 Python 函式稱為 MCP。 |
| Week 05 Frameworks & Orchestration：狀態、分支、停止、人工中斷及同條件前後比較（投影片 4、6、43–46） | LangGraph 候選將畢業進度拆成 load／collect／allocate／evaluate／summarize；另一個學習規劃圖支援 checkpoint、interrupt、YES／NO 後續分支 | `backend/app/graduation_workflow.py`、`backend/week05_langgraph.py`、`backend/compare_framework.py`、`tests/test_week05_langgraph.py`、`docs/week05-graduation/decision.md` | **獨立候選／可切換實作。** 畢業流程預設仍是 `legacy`，需設定 `GRADUATION_ENGINE=langgraph` 才使用候選；整合依賴已包含 SQLite checkpoint，完整 Python suite 已通過，但不代表網站預設採用 LangGraph。 |
| Week 06 Prompt Chaining：固定相依階段、Gate、停止原因（投影片 6–10） | 需求驗證 → 規則排程 → 衝突與完整性 Gate → 模型說明；Gate 未通過時不呼叫下游模型 | `backend/week06_chaining.py`、`frontend/server/studyPlanWorkflow.js`、`frontend/tests/studyPlanWorkflow.test.js`、`docs/week06/adr-001-study-plan-prompt-chaining.md` | 明確 workflow 為**獨立實作並有測試**。目前網站主路由改走 Flask Function Calling，但仍保留固定階段、Gate 與有限停止；報告宜稱「Tool Use 外層的受限 chaining」，不要說所有決策都由 Agent 自主決定。 |
| Week 06 Evaluator–optimizer：初稿、固定規準、有限修訂、同規準重評（投影片 26–28、53–55） | 畢業缺項說明先產生 A，固定規準不通過時最多產生 B；仍不合格就回退基本進度 | `backend/app/graduation_explanation_api.py`、`backend/app/graduation_explanation_core.py`、`docs/week06/GRADUATION_EXPLANATION.md` | **網站已接入流程，模型 live 狀態須另列。** 規則引擎才是畢業判定來源；模型只負責說明，不得說模型判定能否畢業。 |
| Week 07 Semantic Memory：保存可重用偏好，保留來源、確認狀態及更新方式（投影片 6–10、36、79–84） | 保存單一 `study_session_minutes` 偏好；包含 owner、source、version、expiry，支援明確確認、更正、撤回、到期、跨 user 拒絕與 operation ID 冪等 | `backend/app/study_memory.py`、`backend/tests/test_study_memory.py`、`frontend/src/lib/studyMemoryClient.js`、`frontend/tests/plannerApiClient.test.js`、`tests/test_week07_memory.py` | **網站已接入 Flask／SQLite。** 這是 semantic preference memory，不是保存完整聊天；固定 demo user 仍不等於正式登入隔離。 |
| Week 07 記憶有效性：session／TTL、來源更新、撤回後停止新使用（投影片 40、79、83–85） | 畢業說明使用 300 秒 TTL、來源指紋、scope 與重查；來源更新或到期即清除舊說明 | `backend/app/graduation_validity.py`、`frontend/src/lib/graduationMemory.js`、`frontend/tests/graduationMemory.test.js`、`docs/week07/GRADUATION_MEMORY_SCOPE.md` | **網站已接入。** 這是短期衍生結果的有效性控制，不是新的長期使用者記憶。 |

## 每一週可以怎麼示範

### Week 03：資料證據

1. 進入「資料證據」。
2. 指出 source card 的 authority、permission、freshness 與 blocked source。
3. 切換「今日課程與待辦」及「複習安排可行性」，展示 selected evidence 與 citation 一致。
4. 切換「No-answer / coverage failure」，展示沒有即時校務來源時拒答。

報告說法：這一頁驗證 retrieval 後半段的 evidence contract，但 retrieval 排名仍是固定 fixture；尚未建立向量索引。

### Week 04：工具呼叫與安全邊界

1. 進入「智慧學習」，輸入複習需求。
2. 展開執行軌跡，依序指出 request validation、model tool call、tool argument validation、tool execution 及 function response。
3. 用測試或獨立腳本展示未確認的 `save_study_plan` 不寫入，以及相同 `request_id` 重送只回放。

報告說法：目前主畫面完成的是唯讀 Function Calling。寫入工具已實作安全契約，但還沒有接進主畫面；MCP 尚未實作。

### Week 05：LangGraph 編排

1. 啟動後端前設定 `GRADUATION_ENGINE=langgraph`，再開啟「畢業進度」。
2. 說明節點固定，缺規則時走 `unavailable` 分支；框架只負責編排，不改學分規則。
3. 以 `legacy` 重啟即可回退，資料庫不需遷移。

報告說法：這是相同資料與規則下的候選替換，預設仍保留 legacy；沒有證據顯示 LangGraph 在這個短流程一定更快。

### Week 06：受限 Workflow

1. 智慧學習展示固定階段與 Gate；說明不合法輸入、模型改參數及 provider 失敗都有明確停止原因。
2. 畢業進度按下產生說明，說明 A／B 最多一次修訂及失敗回退。

報告說法：學習規劃用 Prompt Chaining 保護前後依賴；畢業說明用 Evaluator–optimizer 控制品質。專案沒有聲稱五種 workflow 全部實作。

### Week 07：偏好記憶與有效期

1. 在智慧學習保存「每次安排時長」，重新整理後讀回。
2. 更正一次，指出 version 增加；撤回後確認不再回填。
3. 畢業說明指出 300 秒 TTL 與來源更新後失效。

報告說法：長期保存的只有已確認時長偏好；私人行程、完整 prompt、模型金鑰與完整聊天都不保存。

## 教師追問時的精準回答

### 為什麼主排程沒有完整 RAG？

排程需要的是本輪已提供的課表、私人行程與確定性衝突規則，不需要從大型外部知識庫搜尋。畢業規則目前也是版本化本機來源，所以核心流程先使用 deterministic rules。Week 03 的 evidence gate 用來驗證引用、來源授權與無答案行為；正式校務文件擴充到多版本、多來源後，才有引入向量檢索的必要。

### 為什麼沒有 MCP？

目前只有單一 Web 應用與少量內部工具，直接 Function Calling 的介面較小，也較容易驗證。MCP 的價值在多個 Host 重用外部 server、工具探索與標準 transport；目前尚沒有這個互通需求。若期末要接校務文件服務或讓多個應用共用工具，再評估 MCP。

### 哪些由模型判斷，哪些由一般程式處理？

- 模型：提出允許的工具呼叫、整理已驗證工具結果、產生畢業缺項說明草稿。
- 一般程式：schema、日期、衝突、排程、學分、來源版本、參數相等 Gate、確認、權限、TTL、撤回、冪等及停止條件。

## 報告前必補或調整的高風險項目

1. 課程要求至少兩個工具介面。現在兩個工具都有程式與測試，但網站主 Agent 只宣告一個唯讀工具；應選擇「把寫入工具安全接入主流程」或「在報告中明確分成主畫面與獨立工具示範」，不可讓觀眾誤以為主模型已在兩者間選擇。
2. `GRADUATION_ENGINE` 預設為 `legacy`。若要展示 Week 05，必須在示範前切成 `langgraph` 並保留啟動證據。
3. Week 03 的 top-k 為 fixture，不得稱為真實 embedding／vector search。
4. MCP 未實作；不得把 REST API、Vite middleware 或 Python 函式誤稱為 MCP。
5. Gemini／OpenAI、fixture／live、`LIVE_NOT_RUN`／`LIVE_FAIL`／`LIVE_PASS` 必須分別標示，不得以測試替身取代真實 provider 證據。

## 2026-11-03 本次重新驗證

| 檢查 | 結果 | 範圍／限制 |
| --- | --- | --- |
| `git diff --check` | PASS | 本次文件沒有空白錯誤 |
| `cd frontend && npm test` | 38 passed | 包含 evidence gate、Prompt Chaining、Flask API client、semantic memory、TTL 與來源更新 |
| `./.venv/bin/python -m pytest tests/test_week04_tools.py backend/tests/test_study_agent_vertex.py -q` | 12 passed | Week 04 工具、Gemini function-call contract 與失敗邊界；provider 為測試替身，不是 live |
| 畢業說明與有效性兩個測試檔 | 39 passed、1 skipped | `backend/tests/test_graduation_explanations.py` 與 `backend/tests/test_graduation_validity.py`；包含 LangGraph 畢業候選，未補足 live provider 項目 |
| `./.venv/bin/python -m pytest` | 356 passed、5 skipped、1 xfailed | 使用 `requirements-integrated.txt` 安裝 Flask 與 Week 02–07 共用依賴 |
| `./.venv/bin/python scripts/verify_environment.py` | PASS | 驗證 Python 3.12、必要模組、專案路徑與 SQLite |
