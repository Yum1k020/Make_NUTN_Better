# 驗證紀錄

日期：2026-11-11（Asia/Taipei）。本次驗證的是未提交工作目錄；精確程式 SHA-256 見 JSON 證據。

## 自動測試

- 新增 Agent API：32 通過，0 失敗。見 [test-evidence.json](test-evidence.json)。
- 完整後端：297 通過，4 跳過，0 失敗。見 [regression-evidence.json](regression-evidence.json)。
- 既有課程 API、profile、planner 的真實 HTTP／重啟測試已在允許 loopback 監聽的環境通過。最初受限沙箱的三個連接埠測試失敗屬環境限制；完整重跑已通過，最終證據為成功那次。
- 跳過項目：既有未登入驗證、雙使用者隔離、正式登入身分映射、舊 planner 的外部 AI 案例。新 Agent API 的模型錯誤邊界另有 stub 測試，不能因此宣稱通過舊版真實外部 AI 測試。
- JavaScript 語法檢查通過；新 HTML/CSS/JS 已格式化；`git diff --check` 通過。

| 驗證情境 | 實際結果 |
| --- | --- |
| 正常 360 分鐘候選 | 多角色交付、來源及時段查證通過，原 planner resources 不變 |
| 時數不足 | 產生 120 分鐘、尚缺 240 分鐘，status=partial |
| 單／多 Agent 同條件 | 相同快照與候選；離線回合 single=3、multi=5 |
| 零空檔 | 尚缺全部時數；commit 回 409 |
| 已有私人行程 | 候選避開忙碌區間 |
| 未知課表時間 | status=failed、SCHEDULE_INCOMPLETE，沒有新增排程 |
| 資料更動 | verify 未通過、commit 409，不留部分寫入 |
| 重複／並行確認 | 同一 run 只建立一份 plan；首次 201，重送 200 |
| 儲存中途失敗 | plan 與 sessions 交易回滾，commit receipt 不變 |
| 已存計畫修改 | 版本查證失敗 |
| 越權／修改原需求／過早交付 | 拒絕工具，不寫入排程，保存失敗紀錄 |
| 重複工具／回合預算／逾時 | 有限停止，保存可查證錯誤 |
| 虛構時數／來源 | UNGROUNDED_RESULT，拒絕交付 |
| OpenAI 傳輸契約 | stub 核對 URL、授權 header、store=false、工具回送及 timeout |
| 用量缺漏 | usage_complete=false，不把未回報量當作真實零成本 |
| 舊入口與 Swagger | `/` 仍轉 `/docs`，原路由保留，新路由加入 OpenAPI |

## 實際 HTTP 獨立工作台

使用 `./scripts/run-agent-lab.sh` 初始化獨立 `agent-lab.sqlite3` 並啟動，透過真實 loopback HTTP 驗證 HTML、JS、CSS、OpenAPI 均回 200；正常 360 分鐘、時數不足 120／240 分鐘兩筆結果、持久化讀取及重新查證皆通過。確認沒有建立 study-plan，原開發資料庫未參與此測試。完整記錄見 [http-smoke.json](http-smoke.json)。

## 瀏覽器操作

使用本機 Brave 實際載入 `/agent-lab`，確認：

- 表單課程與範例從 API 成功載入。
- 未設定 OpenAI 時顯示設定提示，使用離線驗證。
- 點選「產生並驗證」後顯示 6 個時段、已安排 6 h、尚缺 0 h、真實模型呼叫 0。
- 顯示 5 個離線回合與 run ID，沒有把離線結果標記為真實推論。
- 切換「驗證與來源」後，時段、時數、來源、快照等 6 個檢查通過。
- 截圖目視檢查桌面結果頁：表單、時段、分頁、說明及儲存按鈕可讀，未見重疊。

後續瀏覽器控制曾因視窗消失中斷。手機尺寸、下載按鈕與 UI 儲存按鈕尚未完成逐項瀏覽器驗證；底層儲存、重複確認及失敗流程已由 HTTP test client 測試。

## 真實模型與部署界線

本次真實 OpenAI 網路呼叫為 0。成功模型路徑、拒絕越權、錯誤 grounding、缺漏 usage、逾時以 stub 測試；測試證據含 mock_provider 標記。需設定後端 OPENAI_API_KEY 與 OPENAI_MODEL 後，另行執行真實模型比較。

僅本機實作，沒有公開發布，沒有變更原 React 前端。正式登入及多使用者能力仍沿用既有專案限制。本次未提交或推送，因此沒有 candidate commit SHA。
