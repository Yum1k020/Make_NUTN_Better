# Week 05｜畢業規劃：局部換成 LangGraph

將既有「畢業進度／缺項計算」的編排交给 LangGraph StateGraph；保留原來的學分、必修、學程與講座規則。既有入口是 **GET /api/v1/graduation-progress** 與 **GET /api/v1/dashboard** 的畢業摘要。

基準版本：`c06b69f50d4ee66cdc38cf43e1843057c0728f3c`。預設 `legacy`；設定 `GRADUATION_ENGINE=langgraph` 可驗收候選。本次沒有修改複習時段產生功能。

## 作業交付導覽

- [一頁決策](docs/week05-graduation/decision.md)／[PDF](docs/week05-graduation/decision.pdf)
- [前後測試摘要](docs/week05-graduation/acceptance.md)
- [完整證據與環境](docs/week05-graduation/evidence/)
- [程式差異](docs/week05-graduation/framework.patch)
- 原版：Git 基準 commit，以及 `planner_graduation.py::progress_legacy`；候選：`graduation_workflow.py::progress_graph`。

## 盤點：保留／替換／轉接

|責任|原位置|本次處理|
|---|---|---|
|入口與安全保留|planner.py::progress_route、planner_checks.py::dashboard|沿用原 API、使用者歸屬、唯讀 SQLite 交易、回應格式及錯誤處理|
|流程替換|planner_graduation.py::progress|原本手寫讀規則、分支、彙整、計算、摘要；現在選擇 legacy 或 graph|
|原版保留|planner_graduation.py::progress_legacy|原函式本體原樣保存；可獨立核對與回退|
|框架編排|graduation_workflow.py::progress_graph|實際使用 StateGraph、add_node、add_conditional_edges、compile、stream|
|業務保留|document、rules、mappings、programs、lectures、make_check|規則版本與 checksum、分類、必修對照、學程及講座門檻仍由應用維護|
|步驟轉接|load_graduation_context、collect_graduation_credits、allocate_graduation_credits、evaluate_graduation_requirements、finish_graduation_progress|從原 progress 抽出業務步驟；GraduationState 串起資料，不更改判定公式|

```text
原 API／dashboard → progress 選擇 runner
legacy: 原 progress 本體
langgraph: START → load_rules ─有規則→ collect → allocate → evaluate → summarize → END
                            └缺規則→ unavailable → END
規則 checksum 錯誤／資料庫錯誤：原 HTTP 邊界回 500，不偽造達標。
```

盤點確認需自行維護的是步驟順序、缺規則分支與中間資料傳遞；未證明有大量重複 Agent 迴圈。學分演算法不交给框架。為保留可独立對照的原版，抽出的業務步驟與 legacy 有刻意重複，必須計入維護成本。

保留安全與資料規則：只有 finished 且 passed 的課程納入已得學分；修習中／計畫修課不冒充已取得；系選修溢額轉自由選修，不重複採計；分類／課程對照缺漏維持 needs_confirmation；缺規則學分為 null；保留非校方正式認證的 verification_scope。沿用既有狀態優先序：任何 not_met 先決定整體 not_met，個別未知檢查仍標示待確認。

## Windows 重跑與啟動

從專案根目錄（看得到 backend/）執行，Python 3.12。每台裝置使用自己的環境與 SQLite。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-framework.lock.txt
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:LANGSMITH_TRACING = 'false'
cd backend
..\.venv\Scripts\python.exe compare_framework.py --output ../graduation-evidence-rerun.json
$env:GRADUATION_ENGINE = 'langgraph'
..\.venv\Scripts\python.exe -m flask --app app:create_app init-db
..\.venv\Scripts\python.exe -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

開 http://127.0.0.1:5000/docs。先以 PATCH `/api/v1/me` 設定 `{"department_id":"dept-nutn-csie","admission_year":115,"current_semester_id":"semester-115-1"}`，再 GET `/api/v1/graduation-progress`。無修課資料的缺項回應也是正常結果；133 學分全達標用的是測試腳本中的合成資料，不是學生真實紀錄。

回退：停止服務，把 `$env:GRADUATION_ENGINE = 'legacy'` 後重啟。資料庫不需遷移或刪除。拼錯 engine 會在啟動時明確失敗。legacy 不會匯入 LangGraph。

## macOS／Linux

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-framework.lock.txt
cd backend
export PYTHONUTF8=1
LANGSMITH_TRACING=false ../.venv/bin/python compare_framework.py --output ../graduation-evidence-rerun.json
../.venv/bin/python -m flask --app app:create_app init-db
GRADUATION_ENGINE=langgraph LANGSMITH_TRACING=false ../.venv/bin/python -m flask --app app:create_app run --host 127.0.0.1 --port 5000
```

以 `GRADUATION_ENGINE=legacy` 重啟回退。本次實測為 Windows；上面兩平台未實機驗證。

## 回歸測試與證據

在 backend/ 執行 `python -m pytest -k 'not real_http' --evidence ../regression-rerun.json`，分別設定 GRADUATION_ENGINE=legacy、langgraph。使用所建立的虛擬環境 Python；原證據 hook 需要 Git checkout。獨立 compare_framework.py 不需要 Git。

八組 A/B 用完全相同的 SQLite 複本；兩版預期相同，僅排除回應中的 evaluated_at 比較，原時間仍完整保存在證據。每組都核對資料庫雜湊不變、重送不改資料、dashboard 摘要一致，以及真實框架 logger 的節點路徑。

## 完成程度與課程要求

局部框架替換、原入口整合、離線 A/B 與回退已完成。前端仍是既有本機示範原型，本次沒有接回前端。沒有 LLM 接頭，模型請求為 0，模型 live 與自然語言語意驗收仍待完成；不把離線成功寫成 LIVE_PASS。沒有 checkpoint、持久化恢復或寫入授權新增能力。

依教授講義投影片 61、63、67～70（PDF 實體 59、61、65～68 頁）提供程式差異、測試證據、一頁決策。若課程要求模型 live，下一步須先界定畢業規劃的模型說明任務、共用接頭、授權額度、來源充分性與語意驗收，再實測。本包沒有將模型連線或正式畢業資格認證假裝完成。

框架參考：[LangGraph 官方 Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)。本次固定 LangGraph 1.0.3，完整相依版本見 lock 檔。
