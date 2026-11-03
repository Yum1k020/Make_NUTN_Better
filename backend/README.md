# 後端開發環境

目前提供 Flask、Swagger UI、OpenAPI、環境驗證測試，以及固定測試使用者＋SQLite 的 `GET /api/v1/me`、`PATCH /api/v1/me`。另提供課程、學生安排、已確認偏好、畢業規則與 `POST /api/v1/study-agent/run`。React 已透過 `/api/v1` 儲存待辦、私人行程、讀書時段、規劃課程與偏好記憶；智慧學習與畢業缺項說明統一由 Flask 後端呼叫 OpenAI Responses API。尚未建立正式登入，資料仍是本機合成示範內容。

## 位置與分支

- 目前學生安排 API 分支：`feature/student-planner-api-flask`，由課程查詢分支延伸。

- 課程查詢 API 分支：`feature/course-catalog-api`，由使用者資料 API 分支延伸；沿用已決定的 Flask，調整原規格的 FastAPI baseline。
- 使用者資料 API 分支：`feature/user-profile-api`，從 `dev/backend-setup` 建立並保留原本未提交的環境檔案。
- 前端與資料指南已合併至 `main`，原本的前端／文件功能分支已清理；此課程 API 分支尚未合併 `main` 的文件歷史。
- 根目錄的 `nutn_csie_115_graduation_rules.json` 是 115 唯一整合規格；初始化會以內容雜湊載入 SQLite。舊後端快照保留在 legacy 規則 ID，正式認列範圍與部分課程對照仍待提供。
- 後端環境、使用者資料 API 與測試證據一併納入此功能分支；本機資料庫與虛擬環境由 .gitignore 排除。

## 開發工具

- Python 3.12（此次環境為3.12.14）
- Flask：API 服務
- flask-smorest、Marshmallow：輸入驗證、OpenAPI 文件
- swagger-ui-bundle：本機文件網頁資源，不依賴外部 CDN
- pytest：開發測試
- requests：從後端呼叫 OpenAI Responses API；瀏覽器不接觸 API key
- LangGraph：畢業進度唯讀工作流；由 framework lock 一併安裝

確切安裝版本見 `requirements-dev.lock.txt`；執行環境依賴見 `requirements.lock.txt`。`.in` 檔是直接依賴範圍，重建時使用 lock 檔，以免自動升級。

## 啟動

在儲存庫根目錄執行，無需手動啟用虛擬環境：

```sh
./scripts/init-backend-db.sh
./scripts/run-backend.sh
```

第一次使用請先執行 `./scripts/setup-backend.sh` 安裝依賴。初始化可重複執行，不會覆寫個人資料。預設資料庫為 `backend/instance/profile.sqlite3`；可用 `ME_DATABASE=/absolute/path/profile.sqlite3` 指定其他檔案，初始化和啟動必須指定同一路徑。

未指定 `PYTHON_BIN` 時，安裝腳本會優先使用上一層課程環境中已驗證的 Python 3.12，再尋找 `python3.12`。若發現既有 `.venv` 缺少 pip，腳本會停止並提示先將該半成品環境移開，不會在損壞環境中繼續安裝。

更新至學生安排版本後，請再執行一次 `./scripts/init-backend-db.sh`：會保留既有 `/me` 資料、升級學期欄位、建立課程測試資料、安排資源表與版本化畢業草案。查詢 API 本身不會自動建表或寫入種子；未升級的資料庫會回傳 500。日期、課程代碼、先修與校區均為展示資料，詳見課程查詢規格。

- 測試網頁：<http://127.0.0.1:5050/docs>
- 健康檢查：<http://127.0.0.1:5050/api/health>
- OpenAPI：<http://127.0.0.1:5050/openapi.json>

## 前端持久化 API

- 待辦：`GET/POST /api/v1/tasks`、`PATCH/DELETE /api/v1/tasks/{id}`。
- 私人行程：`GET/POST /api/v1/personal-events`、`PATCH/DELETE /api/v1/personal-events/{id}`。
- 讀書計畫：`GET/PUT /api/v1/study-schedule` 會在同一個交易中替換目前計畫及全部時段；單筆調整沿用 `/api/v1/study-sessions/{id}` 與版本檢查。
- 115 修課規劃：`/api/v1/planned-courses`；整合規格的 25 門必修與 35 門選修使用穩定 ID 保存在獨立 `ui_courses` 參照表，不混入既有六筆合成 `/courses` 查詢結果。
- 偏好記憶：`GET/PUT/DELETE /api/v1/study-memory/preference`；保存於 `study_preferences` 與 `study_preference_operations`，保留明確確認、版本、期限、撤回與 operation ID 冪等。

四類個人安排與偏好都使用 `ME_DATABASE` 指定的同一個 SQLite 檔。前端成功遷移舊版 `localStorage` 後會移除四組舊 key；之後瀏覽器不再是主要資料來源。

## OpenAI 後端設定

所有模型流程統一使用 OpenAI Responses API。將設定放在根目錄、已被 Git 忽略的 `.env.local`：

```sh
STUDY_AGENT_PROVIDER=openai
OPENAI_API_KEY=你的金鑰
OPENAI_MODEL=gpt-5-mini
```

`run-backend.sh` 會讀取本機 `.env.local`，但不會輸出其中內容。不得將 API key、access token、`.env` 或 `.env.local` 放入 repository；也不得使用會被打包到瀏覽器的 `VITE_OPENAI_API_KEY`。

- 健康檢查：`GET /api/v1/study-agent/health`。此端點只回報設定提示，`liveChecked=false`，不會假裝已完成真實模型呼叫。
- 主流程：`POST /api/v1/study-agent/run`。只接受固定規劃 schema；OpenAI 工具參數若與使用者需求不一致，工具呼叫會在執行前停止。
- 唯讀工具：`get_validated_study_plan`。寫入工具 `save_study_plan` 仍要求明確確認與 `request_id` 冪等，未放入主示範的自動工具清單。

OpenAI 路徑使用 Responses API 的 strict function tool，仍依序執行「需求驗證 → 模型工具呼叫 → 參數一致性 Gate → 確定性工具 → 工具結果回送模型」。不得使用 `VITE_OPENAI_API_KEY`，因為 `VITE_*` 會被包入瀏覽器程式。`GET /api/v1/study-agent/health` 只回報是否已設定，不會回傳金鑰，也不會執行付費呼叫。

Swagger UI 中可使用 `POST /api/dev/echo`，輸入 `{"message":"測試 Flask API"}` 後按 Try it out／Execute。合法輸入回傳200，空值、缺欄位或型別錯誤回傳422；不會寫入資料。此為環境測試介面，不是業務介面。

只監聽本機，未啟用 debug 或背景常駐服務。按 Ctrl+C 停止。若5050被其他程式使用，可改為 `PORT=5051 ./scripts/run-backend.sh`。目前為開發伺服器，不作正式部署使用。

## 測試

```sh
./scripts/test-backend.sh
# 另存每次實際 HTTP 回應、SQL trace、前後資料及版本雜湊
./scripts/test-backend.sh --evidence=../docs/api/evidence/me-results.json
# 課程查詢版本完整回歸測試（保留歷史 /me 證據，另存新檔）
./scripts/test-backend.sh --evidence=../docs/api/evidence/catalog-results.json
# 學生安排 API（包含既有功能回歸）
./scripts/test-backend.sh --evidence=../docs/api/evidence/planner-results.json
```

驗證環境介面及使用者資料契約、交易回滾、參照資料、部分更新和真實 HTTP 程序重啟後持久保存。測試使用暫存 SQLite，不改動開發資料；重啟測試需要允許監聽 `127.0.0.1`。登入及兩位登入使用者隔離明確標示 skip／未執行。

## 重建環境

需要可使用的 Python 3.12+ 及下載套件的網路。一般 Python 版本符合時：

```sh
./scripts/setup-backend.sh
```

若系統預設 Python 太舊，可指定已安裝的 Python，不會安裝或改動全域 Python：

```sh
PYTHON_BIN=/absolute/path/to/python3.12 ./scripts/setup-backend.sh
```

目前這台電腦使用既有 Codex Python 執行環境建立 `.venv`。該執行環境不是本專案安裝的，也不應隨專案刪除。若將來它被更新或移除，請用可用的 Python 3.12+ 重建 `.venv`。虛擬環境本身不適合搬到其他路徑或電腦，移動專案後也建議重建。

## 隔離與刪除

- 所有新增的 Python 套件都在儲存庫根目錄 `.venv/`，不使用全域 pip 或 `pip --user`。
- 安裝使用 `--isolated --no-cache-dir`；安裝暫存放在 `.cache/tmp/`。
- pytest 快取放在 `.cache/pytest/`；執行腳本禁用 Python bytecode 寫入。
- `.venv/`、`.cache/`、bytecode、私密環境設定與未來本地 instance 資料均由 `.gitignore` 排除。
- 沒有改動 shell 啟動檔、全域 PATH、全域 Git 設定，沒有安裝資料庫伺服器或建立背景服務。
- 前端 npm 套件仍由 `frontend/` 自行管理；業務資料已串接本 Flask 後端。

只想重建 Python 環境：停止服務，在檔案管理器刪除本專案 `.venv` 與 `.cache`，再執行 setup 腳本。請保留原始碼及 lock 檔。

要刪除整個專案：停止服務、關閉使用此環境的終端機（若手動啟用則先 deactivate），刪除整個 `Make_NUTN_Better/` 資料夾即可移除這次安裝的套件、快取與 Git 工作副本。未提交的程式和未來放在裡面的資料也會一起刪除，想保留的內容要先提交或備份。GitHub 遠端分支不受本機刪除影響。

## 後續待決定

此 baseline 使用 Python 內建 sqlite3，無需額外資料庫服務或 ORM。登入方法、正式部署資料庫、資料遷移與部署環境仍待決定；目前固定身分僅供本機開發展示。


## 待辦功能擴充

新增描述、優先級、無截止日期待辦、limit/offset 分頁及 `/api/v1/health` 資料庫檢查，詳見 [契約與舊版差異](../docs/api/task-api-enhancements.md)。此分支沿用 Flask，不需要安裝 FastAPI 或變更 SQLite 表結構。

## 畢業規則整合狀態

113 學年度規則位於 `app/data/nutn_csie_113_graduation_rules_v1.json`，ID 為 `nutn-csie-113-source-v1`，只保留版本化回歸與年度切換能力。

根目錄的 [115 整合規則](../nutn_csie_115_graduation_rules.json) 已成為 `dept-nutn-csie`／115 的啟用版本，ID `nutn-csie-115-integrated-v2`。舊 `mvp-v1` 被移到 legacy 系所鍵以保留查詢歷史；60 分推導預設停用，必須有明確 `passed`。共同認列範圍尚未提供，因此相關已修紀錄回傳待確認而不計入確認學分。

