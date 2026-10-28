# Memory ADR — Route A：保存複習時段偏好

## 狀態

**ADOPT_OFFLINE / LIVE_NOT_RUN**

GitHub Actions run 40618188523 已驗證完整 regression 31 passed, 1 xfailed，Route A offline_all_pass=true。真實 Gemini 狀態獨立維持 LIVE_NOT_RUN。

## 缺口與決定

原智慧排程在新 session 仍需重新提供 session_minutes。因此只加入一個長期偏好 study_session_minutes；使用者明確確認後才保存，新 session 只有在本輪缺少 session_minutes 時才讀回。

## 保留

- scheduler_v1
- preview_study_plan
- Week 04 寫入 study sessions 的確認與 request_id 規則
- Week 05 LangGraph pause/resume
- Week 06 Prompt Chaining Gate
- busy interval、exam date 與原業務規則

## 新增的資料契約

每筆偏好保存：
- owner_id
- preference_type=study_session_minutes
- integer value
- source_type=user_confirmation
- source_id
- version
- created_at
- expires_at
- superseded_at
- revoked_at

## 寫入與讀取安全

- confirmed=False：不寫。
- actor_id != owner_id：不寫。
- value 不在 15..240：不寫。
- 同 request_id 重送：replayed=true，不新增第二筆。
- 更正：新增 v2，v1 superseded。
- 撤回：目前版本 revoked，後續讀不到。
- 到期：不回填。
- 跨 user：forbidden。
- 本輪明確 session_minutes 優先於 memory。

## 為什麼不是整段對話

本週只需要一個穩定、可檢查的設定。整段對話容易混入暫時條件、推論和無關內容，也不利於版本、更正、期限與撤回。

## 實測證據

- Baseline SHA：9e2407a9a9a160b5ca5b51fc6e4a090ba077768e
- Implementation SHA：72380961e4d096b8d334d87d53546f750d4292ac
- CI run：40618188523
- Job：122585522782
- Artifact：12786022642
- Regression：31 passed, 1 xfailed
- offline_all_pass=true

## 代價

新增持久 memory store 與生命週期規則。JSON 適合本週可檢查最小增量，不代表正式多人 production storage。未來若正式上線，應移至有交易、索引與權限控制的資料庫。

## 採用決定

Offline 候選可採用，因為它在不修改 scheduler_v1 的前提下解決重問偏好，且更正、撤回、隔離、期限和冪等都有實際測試證據。

但課堂的本週真實 Gemini 證據尚未執行，所以不能把 ADOPT_OFFLINE 寫成完整 LIVE_PASS。

## 回退

停止使用 preview_with_memory 即回到原本每次明確提供 session_minutes 的流程；scheduler_v1 無需回滾。
