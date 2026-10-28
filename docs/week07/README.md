# Week 07 — Agent Memory Architectures

## 一句話交付

原題目仍是「學生個人安排系統」。本週只選 Route A：保存一個使用者明確確認的 `study_session_minutes`（每次複習分鐘數），新 session 缺少本輪設定時才讀回。

## 記憶邊界

- 只保存 `study_session_minutes`，不保存整段對話、私人行程、考試日期、prompt 或 API key。
- 只有「確認並保存」才寫入；本輪明確輸入永遠優先於記憶。
- 讀回值只預選每次安排時長；排程仍會重新檢查課表、私人行程、考試日期與本次輸入。
- 記憶具有 owner、source、version、expiry 與 revoked / withdrawn 狀態。
- 跨 user 不可讀取；舊版本寫入會拒絕；同 operation / request ID 重送不重複產生副作用。

## 整合後的兩個入口

| 入口 | 用途 | 資料位置 |
| --- | --- | --- |
| Python 課堂驗收 | 離線比較、Gemini live runner、CI 與完整生命週期測試 | `backend/week07_memory.py`、`week07/runtime/memory.json` |
| React 網站 | 讓使用者在「智慧學習」看到、保存、更正與撤回同一個偏好 | `frontend/server/studyMemoryStore.js`、`frontend/data/study-memory.json` |

網站原型的 JSON 與暫存檔已由 `.gitignore` 排除；只提交 schema、API、UI 與測試。這是單機課堂原型，不是正式多實例儲存。

## 網站資料路徑

```text
進入智慧學習
  -> GET /api/study-memory/preference
  -> 驗證使用者、狀態與到期日
  -> 有效 record 回填「每次安排時長」

使用者按「確認並保存」
  -> PUT /api/study-memory/preference
  -> schema / confirmed / expectedVersion / operationId 驗證
  -> 原子寫入 JSON
  -> 實際 record 與版本回填 UI

使用者按「撤回記憶」
  -> DELETE /api/study-memory/preference
  -> 版本驗證
  -> 記錄改為 withdrawn
  -> 後續新讀取回傳 null
```

## 資料契約

| 欄位 | 限制 |
| --- | --- |
| `userId` / `owner` | 同一使用者才能讀寫；目前是本機示範使用者。 |
| `key` / `preference_type` | 固定為 `study_session_minutes`。 |
| `value` | 15–240 分鐘的整數；網站 UI 提供 60、90、120 分鐘快速選項。 |
| `source` | 記錄使用者確認來源，不只保存裸值。 |
| `version` | 保存、更正或撤回會增加；舊 `expectedVersion` 會拒絕。 |
| `expiresAt` | 網站預設 30 天；過期後不再回填。 |
| `operationId` / `request_id` | 相同內容重送只回放原結果。 |

## 驗收矩陣

- 新 session 讀回 v1，並將該值用於原排程。
- 更正後產生新版本，後續只讀最新有效值。
- 撤回後新 session 不再讀到舊值。
- 未確認、非法分鐘數與舊版本寫入都拒絕。
- 跨 user 讀取隔離，過期偏好不回填。
- 同一 operation / request ID 重送不增加 record。
- 原本規則排程、Prompt chaining Gate 與 Agent 失敗 fallback 不回歸。

Python 候選已於 GitHub Actions 驗證 31 passed、1 xfailed，`offline_all_pass=true`。本次整合分支另實測：前端 25/25、Agentic 31 passed / 1 xfailed、Flask 265 passed / 4 skipped、環境必要項目全部通過；瀏覽器交互也完成保存 90 分鐘、重新載入讀回、撤回與行動版檢查，無 console 或 HTTP 錯誤。

## 程式入口

- `backend/week07_memory.py`：Python 記憶生命週期與排程接法。
- `tests/test_week07_memory.py`：Python Route A 測試。
- `week07/live_memory.py`：真實 Gemini proposal、人工確認、寫入、新 session 讀取與摘要。
- `frontend/server/studyMemoryStore.js`：網站 schema、隔離、版本、TTL、撤回與冪等。
- `frontend/server/studyMemoryMiddleware.js`：同源 GET / PUT / DELETE API。
- `frontend/src/components/StudyMemoryPanel.jsx`：明確確認、證據顯示與撤回 UI。
- `frontend/tests/studyMemory.test.js`：網站 Route A 生命週期測試。

## 安全與限制

- `X-Demo-User-Id` 只是本機原型邊界，不是正式登入驗證。
- JSON 檔適合單機課堂驗收；正式多實例部署應改用具交易與權限控制的資料庫。
- 撤回會讓新讀取看不到有效值，但保留本機 operation 證據；完整實體刪除需另定政策。
- 沒有私人 Gemini / OpenAI key 時不宣稱 live pass，也不得提交 `.env`、token、ADC JSON 或真實個資。

架構決策見 [`adr-001-confirmed-study-preference.md`](adr-001-confirmed-study-preference.md)。
