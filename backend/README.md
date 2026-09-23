# 學生個人安排系統 API

第一版提供待辦事項 CRUD，以 Python 3.12、FastAPI 與 SQLite 實作。
資料流程為：前端 HTTP request → 欄位驗證 → SQL → SQLite → JSON response。
這是本機單人原型，尚未提供登入或使用者資料隔離；預設只綁定本機位址。
現有羽球館文件是課堂範例，本 API 不使用那些 fixture。

## 安裝與啟動

在 `Make_NUTN_Better/backend` 目錄執行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

瀏覽 `http://127.0.0.1:8000/docs`，展開端點並按 Try it out 可直接測試。
OpenAPI 規格位於 `/openapi.json`。
首次啟動會建立 `backend/data/planner.sqlite3`；重啟會保留資料。
可用 `PLANNER_DB_PATH` 環境變數指定其他 SQLite 檔案位置。

## 端點

| 方法 | 路徑 | 用途 |
| --- | --- | --- |
| GET | `/api/v1/health` | 檢查服務及資料庫 |
| POST | `/api/v1/tasks` | 新增，回傳 201 |
| GET | `/api/v1/tasks` | 查詢列表 |
| GET | `/api/v1/tasks/{id}` | 查詢單筆 |
| PATCH | `/api/v1/tasks/{id}` | 部分修改 |
| DELETE | `/api/v1/tasks/{id}` | 刪除，回傳 204 空內容 |

列表可使用 `completed=true` 或 `false` 篩選；`limit` 預設 50、最大 200，
`offset` 預設 0。依建立時間由新到舊排序。
不存在的 id 回傳 404，輸入不符合規則回傳 422。

新增範例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"完成資料庫作業","description":"完成 ER 圖","due_at":"2026-10-01T18:00:00+08:00","priority":"high"}'
```

`title` 必填，去除頭尾空白後長度 1–200；`description` 預設空字串、最多 5000 字；
`priority` 為 `low`、`medium` 或 `high`，預設 `medium`；`completed` 預設 false。
`due_at` 可省略或設為 null，日期時間建議包含時區（台灣為 `+08:00`）。
回應包含 UUID `id`、UTC `created_at` 與 `updated_at`。

將回傳的 id 代入，可標記完成：

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/tasks/TASK_ID \
  -H 'Content-Type: application/json' -d '{"completed":true}'
```

PATCH 只更新送出的欄位；以 `{"due_at":null}` 清除期限。其餘欄位不接受 null。
資料庫以參數化 SQL 讀寫；不會在前端 localStorage 儲存這些 API 資料。
目前未串接前端；前端開發時可透過開發伺服器 proxy 將 `/api` 轉送到 8000 埠。

## 測試

```bash
python -m pytest
```

測試使用臨時 SQLite 資料庫，涵蓋 CRUD、篩選、分頁、驗證錯誤、404、
SQL 特殊字元與重新建立 app 後的資料保存。
