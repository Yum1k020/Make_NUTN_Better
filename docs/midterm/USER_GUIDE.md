# 網站使用說明

適用版本：`codex/backend-persistence`，畢業規格 `nutn-csie-115-integrated-v2`。

本網站是課堂用的學生個人安排系統。示範資料使用固定測試使用者與合成行程，待辦、私人行程、讀書時段、讀書時長偏好、規劃課程、課表、已修紀錄與畢業規則由 Flask／SQLite 統一管理。

## 1. 第一次安裝

需求：macOS 或 Linux、Python 3.12、Node.js 20 以上、npm。

```bash
cd "/Users/loise/Documents/代理是人工智慧課程/Make_NUTN_Better"
./scripts/setup-backend.sh

cd frontend
npm ci
cd ..
```

`setup-backend.sh` 會建立 `.venv`，安裝 Flask 與 Week 02–07 共用依賴，執行 `pip check` 及環境驗證。`.venv`、SQLite、`.env.local` 與憑證不會提交 Git。

## 2. 初始化與啟動

終端機一：

```bash
cd "/Users/loise/Documents/代理是人工智慧課程/Make_NUTN_Better"
./scripts/init-backend-db.sh
./scripts/run-backend.sh
```

終端機二：

```bash
cd "/Users/loise/Documents/代理是人工智慧課程/Make_NUTN_Better"
./scripts/select-demo-profile-115.sh
cd frontend
npm run dev
```

開啟 [http://127.0.0.1:5173/](http://127.0.0.1:5173/)。畫面上方應顯示：

> 待辦、行程、讀書時段、課表、課程、修課紀錄與畢業規則已由 Flask／SQLite 管理。

如果 5050 或 5173 已被占用，可改用：

```bash
# 終端機一
PORT=5052 ./scripts/run-backend.sh

# 終端機二
API_BASE=http://127.0.0.1:5052/api/v1 ./scripts/select-demo-profile-115.sh
cd frontend
BACKEND_PROXY_TARGET=http://127.0.0.1:5052 npm run dev -- --port 5175
```

此時網站位址為 [http://127.0.0.1:5175/](http://127.0.0.1:5175/)。

## 3. 今日／本週

這一頁整合課表、待辦、私人行程與讀書時段。

1. 點「新增事項」。
2. 選擇待辦或私人行程，填寫標題、日期與時間。
3. 系統先檢查時間格式與課表衝突，再寫入 Flask／SQLite。
4. 點既有項目可修改；刪除時會再次要求確認。
5. 勾選待辦代表使用者明確修改完成狀態，重新整理後仍會保留。

如果私人行程和課程重疊，系統會拒絕保存並顯示衝突對象。模型不參與衝突判斷。

## 4. 智慧學習

### 4.1 建立讀書計畫

1. 選擇課程與考試日期。
2. 輸入總複習時數。
3. 選擇每次安排時長，以及上午、下午或晚上。
4. 點「用 Agent 產生學習計畫」。
5. 規則工具會避開課表、私人行程與既有讀書時段。
6. 結果可逐筆調整或刪除；刪除時有第二次確認。

一般程式負責 schema、日期、衝突、排程與寫入。模型只能呼叫 allowlist 中的工具，並整理已通過 Gate 的結果。

### 4.2 保存每次讀書時長偏好

1. 在「複習時長記憶」選擇 60、90 或 120 分鐘。
2. 點「確認並保存」。
3. 重新整理後，系統會從 SQLite 讀回偏好並預選時長。
4. 點「撤回記憶」後，新 session 不再使用該偏好。

偏好具有 owner、版本、30 天到期時間與 operation ID。它只會預填輸入，系統仍會重新檢查課表和行程。

### 4.3 Gemini／ADC 狀態

課堂指定主流程使用後端 Google Cloud ADC／Vertex AI Gemini。需要在本機完成 ADC 登入，並在未追蹤的 `.env.local` 設定：

```dotenv
STUDY_AGENT_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_CLOUD_GEMINI_MODEL=your-enabled-model
```

不得把 ADC JSON、token 或 project credential 放入 Git。若沒有設定，規則排程仍可運作，但真實模型證據必須標示 `LIVE_NOT_RUN`。

後端另保留 OpenAI Responses API 選用介面：

```dotenv
STUDY_AGENT_PROVIDER=openai
OPENAI_API_KEY=your-server-side-key
OPENAI_MODEL=gpt-5-mini
```

金鑰只可放在伺服器端 `.env.local`，不可使用 `VITE_OPENAI_API_KEY`。

## 5. 修課規劃

1. 進入「修課規劃」。
2. 確認規格標示為 `nutn-csie-115-integrated-v2`。
3. 可搜尋 25 門專業必修與 35 門專業選修。
4. 點「加入規劃」後，課程寫入 SQLite。
5. 點「移出規劃」會先要求確認。

規劃課程不等於已修、通過或取得學分，不會自動增加畢業學分。

## 6. 畢業進度

畢業頁由一般程式讀取 115 規則、已修紀錄、講座與學程資料後逐項計算。

- 最低總學分：133。
- 系專業必選修：81 學分，其中必修 69、選修至少 12。
- 學術講座與學程證書分開檢核。
- `null` 表示資料待確認，不等於 0。
- 共同認列範圍尚未提供，所以通過紀錄可能顯示 `RECOGNITION_PENDING`。
- 正式畢業資格仍以校方審核為準。

按「產生說明」時，模型只接收去識別的彙整狀態。說明最多保存 300 秒，來源更新、到期或新工作階段都會清除舊內容。

## 7. 資料證據

「資料證據」展示 Week 03 的 source card、固定查詢、citation audit 與 no-answer 行為。這是 evidence-gate prototype；目前排名與 top-k 是固定測試資料，沒有向量資料庫、embedding 或正式 RAG ingestion，因此報告中不可稱為完整 RAG。

## 8. 資料安全與操作界線

- 只使用合成或去識別資料。
- 固定 demo user 只適合本機課堂示範，不等於正式身分驗證。
- 低風險新增與修改以使用者點擊保存按鈕作為明確意圖。
- 刪除待辦、行程、讀書時段與規劃課程會要求第二次確認。
- 偏好寫入必須 `confirmed=true`；重送使用 operation ID 與版本檢查。
- `save_study_plan` 工具需要 `confirmed=true` 與 `request_id`，相同請求不會重複寫入。
- 模型不能直接決定學分、衝突、權限或資料庫結果。

## 9. 報告前驗證

```bash
cd "/Users/loise/Documents/代理是人工智慧課程/Make_NUTN_Better"
.venv/bin/python scripts/verify_environment.py
.venv/bin/python -m pytest

cd frontend
npm test
npm run build
npm run format:check
```

2026-11-03 的重新驗證結果為 Python 356 passed、5 skipped、1 xfailed；Frontend 38/38；build 與 format 均通過。skip、xfail 與 provider 未執行不能說成通過。

## 10. 常見問題

### 畫面顯示 113 或找不到 v2 規格

先確認新版 Flask 已啟動，再執行：

```bash
./scripts/select-demo-profile-115.sh
```

### 出現 `No module named flask` 或缺 FastAPI／LangGraph

重新執行：

```bash
./scripts/setup-backend.sh
```

### Agent 失敗但仍看到排程

這是預期 fallback。規則工具的結果仍可使用；模型呼叫失敗必須另外標示 `LIVE_FAIL` 或 `LIVE_NOT_RUN`。

### 畢業進度顯示待確認

先檢查已修紀錄、認列範圍、課程對照、講座與學程資料。系統不會把缺資料自動當成零或已完成。
