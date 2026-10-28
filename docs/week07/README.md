# Week 07：智慧學習的已確認偏好記憶

## 一句話交付

我們保留原本的 React、Vite、規則排程與 OpenAI Agents SDK，只在「智慧學習」加入一筆可檢查的長期記憶：使用者明確確認的常用學習時段可在新 session 讀回，也能更正、到期與撤回。

## 範圍與版本

- 原題目：學生個人安排系統。
- 選定路線：A「保存一個已確認欄位」。
- Baseline SHA：[`2b47fb4`](https://github.com/Yum1k020/Make_NUTN_Better/commit/2b47fb4)。
- Candidate SHA（程式與測試）：[`4d83d26`](https://github.com/Yum1k020/Make_NUTN_Better/commit/4d83d26)。
- 固定任務：學生設定考試日期、複習時數與可用時段，系統避開課程及私人行程產生計畫。
- 本週增量：只保存 `preferredStudyPeriod`，不保存整段對話、私人行程、考試日期或 API key。
- 保留：既有 Prompt chaining、衝突 Gate、規則排程、Agent 說明與失敗 fallback。

## 缺口與選路線

原版每次進入「智慧學習」都以固定的「下午＋晚上」開始。即使使用者長期習慣晚上學習，新 session 仍要重新調整。這是會重複發生、答案可驗證的偏好缺口，因此選擇路線 A；本週不加入事件記憶、多 Agent 共享、向量資料庫或完整對話摘要。

## What、When、How

| 問題 | 本專案的決定                                                                                                                          |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------- |
| What | 保存 `morning`、`afternoon`、`evening` 之一，連同 owner、來源、版本、狀態與到期時間。                                                 |
| When | 使用者按「確認並保存」才寫入；進入智慧學習頁時讀取；30 天到期或撤回後停止新讀取。                                                     |
| How  | 前端呼叫同源記憶 API，伺服器驗證身分、schema、確認旗標、預期版本與 operation ID，再以原子檔案替換保存。工具結果回到 UI 後才顯示成功。 |

暫時勾選的可安排時段仍只是本次條件，不會因產生計畫而自動變成長期偏好。讀回偏好只預選時段，排程仍會重新檢查課表、私人行程、考試日期與本次輸入。

## 資料契約

| 欄位               | 用途與限制                                                    |
| ------------------ | ------------------------------------------------------------- |
| `userId` / `owner` | 將記憶限制在同一位示範使用者；不同 user 不共享。              |
| `key`              | 固定為 `preferredStudyPeriod`，避免任意欄位寫入。             |
| `value`            | 只能是 `morning`、`afternoon`、`evening`；撤回後清為 `null`。 |
| `source`           | 固定記錄 `user-confirmed` 與 `study-planner`。                |
| `version`          | 每次有效更新或撤回加一；舊 `expectedVersion` 會被拒絕。       |
| `expiresAt`        | 保存後 30 天；過期記錄不再回填前端。                          |
| `operationId`      | 同一操作重送只回放原結果；相同 ID 搭配不同內容會拒絕。        |
| `status`           | `active` 或 `withdrawn`；只有未過期的 `active` 可被讀回。     |

實際資料預設寫入 `frontend/data/study-memory.json`，該檔與暫存檔已由 `.gitignore` 排除。Git 只提交 schema、工具、UI 與測試。

## 完整資料路徑

```text
新 session 進入智慧學習
  -> GET /api/study-memory/preference
  -> 身分與有效期檢查
  -> 有效 record 回填 UI
  -> 預選常用時段

使用者明確按下確認並保存
  -> PUT /api/study-memory/preference
  -> schema / confirmed / expectedVersion / operationId 驗證
  -> 原子寫入 JSON
  -> 實際 record 與版本回填 UI

使用者撤回
  -> DELETE /api/study-memory/preference
  -> 版本驗證
  -> value 清除、狀態改為 withdrawn、版本加一
  -> 後續新讀取回傳 null
```

## 測試矩陣：預期與實際

| 案例               | 預期                                                 | 實際與證據                                                             |
| ------------------ | ---------------------------------------------------- | ---------------------------------------------------------------------- |
| C01 原主流程       | Week 06 規則與 Agent 主流程不回歸                    | `npm test` 24/24；`npm run agent:smoke` 完成四階段，360 分鐘、尚缺 0。 |
| A1 新 session      | 保存後由新的 store instance 讀到同 ID、值與版本      | `week07 A1` 通過。                                                     |
| A2 更正            | 新值成為 v2；舊版本寫入拒絕                          | `week07 A2` 通過。                                                     |
| A3 撤回            | 新讀取不再取得舊值                                   | `week07 A3` 通過。                                                     |
| C02 跨 user        | U002 讀不到 U001 的偏好                              | `week07 C02` 通過。                                                    |
| 到期排除           | 測試時鐘超過期限後不回填                             | `week07 boundary: expired preference` 通過。                           |
| W01 未授權／未確認 | 缺少身分或 `confirmed: true` 時不產生檔案            | 兩條拒絕測試通過。                                                     |
| W02 重送           | 同一 operation ID 只產生一筆 record 與一筆 operation | `week07 W02` 通過，版本保持 v1。                                       |

## 原版與候選比較

| 比較層             | Baseline `2b47fb4`       | Candidate `4d83d26`                                      |
| ------------------ | ------------------------ | -------------------------------------------------------- |
| 檢索是否讀對       | 沒有長期偏好工具         | 只回傳同 user、有效、未撤回的目前版本。                  |
| 回答／畫面是否用對 | 每次固定勾選下午與晚上   | 新 session 會預選已確認時段；使用者仍可修改本次條件。    |
| 任務是否完成       | 產生可檢查的複習計畫     | 原任務保持不變，另完成保存、更正、到期與撤回。           |
| 失敗邊界           | Agent 失敗時保留規則排程 | 記憶 API 失敗時仍可手動設定；不阻止原排程。              |
| 隱私範圍           | 私人行程只在規劃請求使用 | 長期記憶不含私人行程，實際 JSON 不進 Git，也不送給模型。 |

## UI 與真實路徑證據

- 日期：2026-10-28。
- 桌面流程：保存「晚上」為 v1 → 重新載入並重新進入智慧學習 → UI 顯示「已從新 session 讀回」且只預選晚上 → 撤回 → 再載入後顯示沒有有效偏好。
- 行動版：390 × 844 檢查記憶面板、兩個操作按鈕、證據欄位與底部導覽，沒有水平溢位。
- Console：上述流程沒有相關 `error` 或 `warn`。
- 真實 Agent：`week06-86d1ea5e-4647-499a-99fa-e8648d892a7c`，狀態 `completed`，三個時段、360 分鐘、尚缺 0。
- 記憶保存與讀回是確定性後端工具，不會額外呼叫模型；真實 Agent smoke 用固定合成課名、日期與空私人行程，未讀取記憶檔。

## 程式與復現

- `frontend/server/studyMemoryStore.js`：資料契約、隔離、版本、TTL、撤回與冪等。
- `frontend/server/studyMemoryMiddleware.js`：同源 GET／PUT／DELETE API 與安全錯誤。
- `frontend/src/lib/studyMemoryClient.js`：瀏覽器端記憶 API client，不包含 API key。
- `frontend/src/components/StudyMemoryPanel.jsx`：明確確認、證據顯示與撤回 UI。
- `frontend/tests/studyMemory.test.js`：路線 A、跨 user、到期、未授權與重送案例。

```bash
cd frontend
npm test
npm run build
npm run format:check
npm run agent:smoke

cd ../..
./.venv/bin/python -m pytest
./.venv/bin/python scripts/verify_environment.py
```

## 已知限制與採用決定

- 目前只有固定示範 user，`X-Demo-User-Id` 是本機原型邊界，不是正式驗證；正式部署前必須由登入 session 在伺服器端決定 user ID。
- 檔案儲存適合單機課堂原型，不適合多實例並行部署；正式環境應改用具交易與權限控制的資料庫。
- 「撤回」會讓新讀取看不到有效值並清除目前欄位，但 operation 證據仍留在本機檔案；若要求完整實體刪除，需另定備份、稽核與刪除政策。
- 本週沒有證明降低 token、費用或排程時間；改善的是跨 session 重複設定與記憶生命週期的可驗證性。
- 依上述測試與 UI 證據，採用這個單欄位記憶增量；不擴充到向量檢索或完整對話記憶。

設計理由與替代方案見 [`adr-001-confirmed-study-preference.md`](adr-001-confirmed-study-preference.md)。
