# Week 04：局部框架替換決策

## 結論

本週只替換「智慧學習」的 AI 執行層：移除瀏覽器直接呼叫 Responses API 的手刻程式，改用伺服器端 OpenAI Agents SDK。原本的 `planStudySessions()` 排程、衝突檢查與時間不足規則全部保留，不把確定性規則交給語言模型重做。

## 為什麼替換這一塊

1. **安全邊界較正確：** 原作法使用 `VITE_OPENAI_API_KEY`，Vite 會把 `VITE_*` 變數提供給瀏覽器，因此金鑰可能出現在前端執行環境。替換後只有伺服器讀取 `OPENAI_API_KEY`，前端只送規劃資料到同源 API。
2. **減少重複維護：** 原本要自行組 request、解析 response、處理工具流程與錯誤；Agents SDK 統一處理 Agent 執行迴圈、function tool 與 structured output。
3. **保留可驗證規則：** 排程不能靠模型猜測。框架必須呼叫 `get_validated_study_plan`，該工具包住原本的規則引擎；即使 Agent 失敗，畫面仍保留規則排程。
4. **容易測試：** Agent runner 可以注入假實作，測試能比較替換前後的 `scheduledMinutes`、`remainingMinutes` 與 sessions，無須每次連線或消耗 API 額度。
5. **符合專題主題：** Agent 不只是生成一段文字，而是實際協調既有排程工具、讀取工具結果，再用結構化格式向學生說明。
6. **範圍最小：** 本次沒有更換 React、Vite、資料模型或新增資料庫，只局部替換一個 AI 執行入口，較容易用同案例比較採用前後的差異。

## 前後差異

```text
替換前
瀏覽器 UI -> 手刻 fetch -> OpenAI Responses API
             \-> VITE_* 金鑰位於前端環境

替換後
瀏覽器 UI -> /api/study-agent/run -> Agents SDK Agent
                                      -> function tool
                                      -> 原 planStudySessions 規則
```

## 保留的功能與安全規則

- 考試日期必須晚於規劃起始日。
- 複習時段不能與固定課程、私人行程或其他複習時段重疊。
- 可用時間不足時回報 `remainingMinutes`，不製造衝突時段。
- 使用者仍可手動調整或刪除產生的時段。
- Agent 回傳排程若與本機規則結果不同，前端拒絕採用並保留原結果。
- tracing 預設關閉，API key、`.env.local` 與個人資料不得提交 Git。

## 驗收案例

| 案例 | 預期結果 |
| --- | --- |
| 2026-09-17 至 2026-09-24、需要 6 小時、每次 2 小時 | 產生 3 個時段、共 360 分鐘、尚缺 0 分鐘，且不衝突 |
| 2026-09-17 至隔日、只允許上午、需要 10 小時 | 不建立衝突時段，回報尚缺 600 分鐘 |
| Agent API 暫時失敗 | 顯示錯誤說明，但保留原規則排程 |
| 建置前端 | bundle 中不包含 `OPENAI_API_KEY` 或 `VITE_OPENAI_API_KEY` |

## 代價與限制

- 開發環境需使用 Node.js 22 以上版本。
- 使用者按下 Agent 規劃後，課程名稱、日期、可用時段與目前私人行程會送到 OpenAI；目前資料是 fixture，正式上線前仍需補上告知、最小化與權限設計。
- CLI smoke test 只使用合成課名與空的私人行程，避免為了驗收把專案 fixture 行程送到外部服務。
- Agent 說明需要網路、會增加等待時間並產生 API 用量；確定性排程本身不依賴模型。
- 目前 Vite middleware 是本機原型用的伺服器入口，正式部署時應移到受控後端，而不是把 API key 放回靜態網站。

## 決策

**採用 Agents SDK 版本。** 理由不是「框架一定比較好」，而是此處剛好需要工具呼叫、結構化輸出與伺服器端金鑰邊界；同時以原規則作為唯一排程依據，能把框架的優點限制在它真正擅長的協調與說明工作。
