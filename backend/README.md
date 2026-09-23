# 後端開發環境

目前提供 Flask、Swagger UI、OpenAPI、環境驗證測試，以及固定測試使用者＋SQLite 的 `GET /api/v1/me`、`PATCH /api/v1/me`。完整規格、驗收案例與真正執行的測試證據見 [使用者資料 API](../docs/api/me.md)。尚未建立登入、畢業審核或排程 API；既有前端仍使用自己的示範資料。

## 位置與分支

- 使用者資料 API 分支：`feature/user-profile-api`，從 `dev/backend-setup` 建立並保留原本未提交的環境檔案。
- 已抓取並建立追蹤分支：`main`、`codex/frontend-student-planner`、`docs/data-guide`。
- 工作目錄內的 `DATA_GUIDE.md` 與規則 JSON 複製自 `origin/docs/data-guide`，尚未提交或合併文件分支的歷史。
- 後端環境、使用者資料 API 與測試證據一併納入此功能分支；本機資料庫與虛擬環境由 .gitignore 排除。

## 開發工具

- Python 3.12（此次環境為3.12.14）
- Flask：API 服務
- flask-smorest、Marshmallow：輸入驗證、OpenAPI 文件
- swagger-ui-bundle：本機文件網頁資源，不依賴外部 CDN
- pytest：開發測試

確切安裝版本見 `requirements-dev.lock.txt`；執行環境依賴見 `requirements.lock.txt`。`.in` 檔是直接依賴範圍，重建時使用 lock 檔，以免自動升級。

## 啟動

在儲存庫根目錄執行，無需手動啟用虛擬環境：

```sh
./scripts/init-backend-db.sh
./scripts/run-backend.sh
```

第一次使用請先執行 `./scripts/setup-backend.sh` 安裝依賴。初始化可重複執行，不會覆寫個人資料。預設資料庫為 `backend/instance/profile.sqlite3`；可用 `ME_DATABASE=/absolute/path/profile.sqlite3` 指定其他檔案，初始化和啟動必須指定同一路徑。

- 測試網頁：<http://127.0.0.1:5050/docs>
- 健康檢查：<http://127.0.0.1:5050/api/health>
- OpenAPI：<http://127.0.0.1:5050/openapi.json>

Swagger UI 中可使用 `POST /api/dev/echo`，輸入 `{"message":"測試 Flask API"}` 後按 Try it out／Execute。合法輸入回傳200，空值、缺欄位或型別錯誤回傳422；不會寫入資料。此為環境測試介面，不是業務介面。

只監聽本機，未啟用 debug 或背景常駐服務。按 Ctrl+C 停止。若5050被其他程式使用，可改為 `PORT=5051 ./scripts/run-backend.sh`。目前為開發伺服器，不作正式部署使用。

## 測試

```sh
./scripts/test-backend.sh
# 另存每次實際 HTTP 回應、SQL trace、前後資料及版本雜湊
./scripts/test-backend.sh --evidence=../docs/api/evidence/me-results.json
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
