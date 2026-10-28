# Memory ADR — Route A：保存複習時段偏好

## 狀態

Accepted for candidate validation。離線控制與回歸通過後可採用；Week 07 真實 Gemini 狀態獨立記錄，不用 offline 結果代替。

## 缺口與決定

缺口：原智慧排程在新 session 仍要重新提供 session_minutes。

決定：只加入一個長期偏好 study_session_minutes。使用者明確確認後才保存；新 session 在沒有明確 session_minutes 時才讀回。

## 保留

- scheduler_v1
- preview_study_plan
- Week 04 寫入 study sessions 的確認與 request_id 規則
- Week 05 LangGraph pause/resume
- Week 06 Prompt Chaining Gate
- 原本 busy interval 與 exam-date 規則

## 新增

- owner 隔離
- source
- version
- expiry
- correction / supersede
- revocation
- request_id idempotency
- controlled read

## 為什麼不是保存整段對話

本週只需要一個穩定、可檢查的設定。整段對話容易把暫時條件、推論與無關內容一起帶入，也不利於版本、更正與撤回。

## 讀取優先規則

1. 當前 request 有明確 session_minutes：使用當前值。
2. 當前 request 缺少 session_minutes：才讀有效偏好。
3. 記憶跨 user、撤回、過期或不存在：不可使用。

因此記憶不能蓋過本輪明確輸入。

## 寫入安全

- confirmed=False：不寫。
- actor_id != owner_id：不寫。
- 非法 value：不寫。
- 同 request_id 重送：replayed=true，不增加第二筆。
- 更正：新增新 version，舊版 superseded。
- 撤回：目前版本 revoked，後續讀取排除。

## 替代方案

- Route B 事件記憶：目前缺口不是「不知道做過什麼」。
- Route C session 清除：能避免錯留暫時條件，但無法解決每次重問 60 分鐘偏好。
- Route D 角色共享：目前沒有必要為此偏好開放另一個角色。

## 代價

- 增加一個持久 memory store 與生命週期規則。
- 需要處理版本、期限、撤回與權限。
- 偏好可能過時，因此不能沒有 expiry / revoke。
- 真實多人環境不應以單一 JSON 檔作正式資料庫；本週 JSON 是可檢查的最小增量。

## 採用判準

同一批案例必須證明：新 session 讀對、跨 user 拒絕、更正讀新版、撤回後不可見、未確認不寫、重送不多寫、原排程結果不退步。

## 回退

本週新增檔案，不修改 scheduler_v1。停止使用 preview_with_memory 即回到原本每次明確傳 session_minutes 的流程。
