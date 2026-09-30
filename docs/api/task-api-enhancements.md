# 待辦 API 擴充

分支：`feature/task-api-enhancements`，基於 main `4b13948`。
移植來源：`codex/student-planner-api` 的 `80ead4c9eec03b0773f869f1277e0b38f092cc5b`。
舊分支原始碼、測試與羽球課堂範例保留於 `archive/student-planner-api-fastapi` 標籤；不將 FastAPI、Uvicorn 或羽球資料混入 Flask。

## 新增與修改

`POST /api/v1/tasks` 現在只要求 title，其餘舊欄位仍可提供。

| 欄位 | 規則 |
| --- | --- |
| title | 必填，去除頭尾空白後 1～200 字元 |
| type | 預設 todo；原本 assignment/report/exam/review 保留 |
| description | 可省略，預設空字串，去除頭尾空白後最多 5000 字元，不接受 null |
| priority | low/medium/high，預設 medium，不接受 null |
| due_date | 可省略或 null，表示無截止日期 |
| due_time | 無日期時不能提供非 null 時間；PATCH 清除日期會一併清除時間 |

PATCH 未提供欄位時保留舊值；description="" 清空描述。已被複習計畫引用的考試待辦，仍禁止清除其日期或破壞關聯（409）。

```json
{"title":"整理筆記","description":"整理第三章","priority":"high"}
```

無期限待辦會留在一般待辦清單，但不納入有 from/to 的日期篩選、行事曆期限、首頁當日與未來七日期限摘要。

## 清單分頁

`GET /api/v1/tasks?limit=20&offset=0&completed=false`

- limit 預設 50，最小 1，最大 200；offset 預設 0，最小 0。
- from/to/completed/course_id 篩選先執行，再分頁。
- 排序維持 Flask 的截止日期、截止時間與 task_id；無日期排最後，同日無時間排在有時間之後。
- meta.count 為當頁筆數；meta.total 為篩選後總筆數，另外回傳 limit/offset。
- **行為變更：未提供參數時最多回傳 50 筆。呼叫端需要分頁取得剩餘資料。**
- 目前在讀取與驗證本人資源後以記憶體分頁，減少回應大小，尚未提供 SQL 層大資料量最佳化。翻頁間新增、刪除或改動排序欄位，可能造成位置移動。

## 舊資料與來源差異

SQLite 表結構不變，欄位存於 planner_resources.body JSON。讀取舊待辦時僅對缺少的 description/priority 補預設值，不因 GET 寫入資料庫；之後 PATCH 才會保存補齊後資料。既有日期與其他必需儲存欄位損壞仍會回報錯誤。

這是功能移植，不是 FastAPI HTTP 契約的完整相容層：

- 保留 Flask 的 task_id、data/meta 回應格式與 due_date/due_time，不引入舊版 id 或 due_at。
- 舊版依建立時間倒序，這裡保留 Flask 截止日期順序。
- 既有 CRUD、完成狀態篩選、404、輸入驗證、交易與持久化沿用 Flask。
- 舊 FastAPI 的 backend/data/planner.sqlite3 不會自動匯入；此變更不讀寫該檔。
- 新增 `GET /api/v1/health`：查詢使用者及 planner_resources 表，成功回傳 `{"status":"ok"}`；錯誤使用現有 500 error 格式。原 `/api/health` 不變。
- 前端尚未串 API，此次沒有加入描述／優先級輸入畫面。

## 驗證

執行 `sh scripts/test-backend.sh`。新增測試涵蓋欄位保存、重新建立 app 後持久化、舊 JSON 相容且 GET 不寫入、PATCH 清空與原子性、日期摘要、分頁邊界與穩定排序、考試關聯保護、OpenAPI 及資料庫健康檢查。

本次完整回歸結果：**265 passed、4 skipped**。略過項目沿用既有正式登入／雙使用者隔離及外部 AI 未實作情境。
