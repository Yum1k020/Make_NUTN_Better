# 後端開發環境

目前提供 Flask、Swagger UI、OpenAPI、環境驗證測試，以及固定測試使用者＋SQLite 的 `GET /api/v1/me`、`PATCH /api/v1/me`。另提供課程、學生安排、畢業規則與 `POST /api/v1/study-agent/run`。智慧學習 Agent 透過 Google Cloud ADC 呼叫 Vertex AI Gemini；尚未建立正式登入，前端仍含本機示範資料。

## 位置與分支

- 目前學生安排 API 分支：`feature/student-planner-api-flask`，由課程查詢分支延伸。

- 課程查詢 API 分支：`feature/course-catalog-api`，由使用者資料 API 分支延伸；沿用已決定的 Flask，調整原規格的 FastAPI baseline。
- 使用者資料 API 分支：`feature/user-profile-api`，從 `dev/backend-setup` 建立並保留原本未提交的環境檔案。
- 前端與資料指南已合併至 `main`，原本的前端／文件功能分支已清理；此課程 API 分支尚未合併 `main` 的文件歷史。
- 根目錄的 `DATA_GUIDE.md` 與整合規則 JSON 不直接匯入；初始化使用已納入 `backend/app/data/` 的版本化規則副本，正式課程對照仍待確認。
- 後端環境、使用者資料 API 與測試證據一併納入此功能分支；本機資料庫與虛擬環境由 .gitignore 排除。

## 開發工具

- Python 3.12（此次環境為3.12.14）
- Flask：API 服務
- flask-smorest、Marshmallow：輸入驗證、OpenAPI 文件
- swagger-ui-bundle：本機文件網頁資源，不依賴外部 CDN
- pytest：開發測試
- google-auth：只在後端透過 ADC 取得短期 access token
- requests：從後端呼叫 OpenAI Responses API；瀏覽器不接觸 API key

確切安裝版本見 `requirements-dev.lock.txt`；執行環境依賴見 `requirements.lock.txt`。`.in` 檔是直接依賴範圍，重建時使用 lock 檔，以免自動升級。

## 啟動

在儲存庫根目錄執行，無需手動啟用虛擬環境：

```sh
./scripts/init-backend-db.sh
./scripts/run-backend.sh
```

第一次使用請先執行 `./scripts/setup-backend.sh` 安裝依賴。初始化可重複執行，不會覆寫個人資料。預設資料庫為 `backend/instance/profile.sqlite3`；可用 `ME_DATABASE=/absolute/path/profile.sqlite3` 指定其他檔案，初始化和啟動必須指定同一路徑。

更新至學生安排版本後，請再執行一次 `./scripts/init-backend-db.sh`：會保留既有 `/me` 資料、升級學期欄位、建立課程測試資料、安排資源表與版本化畢業草案。查詢 API 本身不會自動建表或寫入種子；未升級的資料庫會回傳 500。日期、課程代碼、先修與校區均為展示資料，詳見課程查詢規格。

- 測試網頁：<http://127.0.0.1:5050/docs>
- 健康檢查：<http://127.0.0.1:5050/api/health>
- OpenAPI：<http://127.0.0.1:5050/openapi.json>

## Gemini／ADC 設定

主示範不使用 API key，後端依 Google Cloud Application Default Credentials 的標準順序尋找憑證。非敏感設定如下：

```sh
export GOOGLE_CLOUD_PROJECT="你的 Google Cloud project ID"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_CLOUD_GEMINI_MODEL="gemini-2.5-flash"
```

本機可使用 `gcloud auth application-default login` 建立 ADC。正式 Google Cloud 環境應使用綁定服務帳號與最小權限。不得將 ADC JSON、access token、API key 或 `.env` 放入 repository。

- 健康檢查：`GET /api/v1/study-agent/health`。此端點只回報設定提示，`liveChecked=false`，不會假裝已完成真實模型呼叫。
- 主流程：`POST /api/v1/study-agent/run`。只接受固定規劃 schema；Gemini 工具參數若與使用者需求不一致，工具呼叫會在執行前停止。
- 唯讀工具：`get_validated_study_plan`。寫入工具 `save_study_plan` 仍要求明確確認與 `request_id` 冪等，未放入主示範的自動工具清單。

## 選用 OpenAI 後端介面

課堂主流程仍以 `STUDY_AGENT_PROVIDER=vertex` 為預設，符合 Gemini／ADC 驗收要求。若後續要改用 OpenAI，將真實金鑰只放在根目錄、已被 Git 忽略的 `.env.local`：

```sh
OPENAI_API_KEY=你的金鑰
OPENAI_MODEL=gpt-5-mini
```

啟動時指定供應者；`run-backend.sh` 會讀取本機 `.env.local`，但不會輸出其中內容：

```sh
STUDY_AGENT_PROVIDER=openai ./scripts/run-backend.sh
```

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
- 沒有安裝前端 npm 套件；目前前端原始碼已抓取但尚未串接後端。

只想重建 Python 環境：停止服務，在檔案管理器刪除本專案 `.venv` 與 `.cache`，再執行 setup 腳本。請保留原始碼及 lock 檔。

要刪除整個專案：停止服務、關閉使用此環境的終端機（若手動啟用則先 deactivate），刪除整個 `Make_NUTN_Better/` 資料夾即可移除這次安裝的套件、快取與 Git 工作副本。未提交的程式和未來放在裡面的資料也會一起刪除，想保留的內容要先提交或備份。GitHub 遠端分支不受本機刪除影響。

## 後續待決定

此 baseline 使用 Python 內建 sqlite3，無需額外資料庫服務或 ORM。登入方法、正式部署資料庫、資料遷移與部署環境仍待決定；目前固定身分僅供本機開發展示。


## 待辦功能擴充

新增描述、優先級、無截止日期待辦、limit/offset 分頁及 `/api/v1/health` 資料庫檢查，詳見 [契約與舊版差異](../docs/api/task-api-enhancements.md)。此分支沿用 Flask，不需要安裝 FastAPI 或變更 SQLite 表結構。

## 畢業規則整合狀態（2026-10-03）

根目錄的新 [整合規則](../nutn_csie_115_graduation_rules.json) 與 [決策紀錄](../docs/decisions/CHANGE_DECISIONS.md) 是目標規格。後端目前仍使用 `app/data/nutn_csie_115_graduation_rules_v1.json`，尚未實作共同認列範圍、證書推定狀態或可停用的60分政策。不要直接替換該快照；後續需完成程式與資料遷移。

