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


---

## 畢業功能線文件（原始分支內容）

# Memory ADR｜畢業說明 TTL（C 路線）

**狀態：條件採用。** 離線證據支持本機原型採用；LIVE 與正式跨 user 驗收待補。

**問題與決定。** 畢業資料會更新，已核對過的說明只代表當次快照。原版在模型執行期間資料改變後仍回傳舊 verified 說明。選 C 的 TTL 到期排除：說明有效 300 秒，來源改變或工作階段改變即停止使用；不新增長期學生偏好。

**資料契約。** 來源指紋由後端進度及規則 digest 產生；伺服器給 scope_id、issued_at、expires_at，前端記憶只保存當頁說明。每次新生成都重讀資料；I/O 後重查，通過原固定 evaluator 才顯示。背景來源變更由 15 秒輪詢及回頁重查發現，不宣稱即時同步。

**保留與修改。** 保留 Gemini、LangGraph/legacy 切換、RAG/規則來源責任、unknown 語意、唯讀學分計算及原有停止上限。只加有效範圍、前後來源檢查與延遲回應保護。清除說明不刪 SQLite 或備份。

**替代方案與代價。** A 的學分上限偏好需要新規劃邏輯，超出目前唯讀缺項說明終點；永久保存說明會增加失效與隱私責任。選 C 代價是每個有效頁面約每分鐘四次來源查詢，且更新後要重新產生說明；不聲稱降低 token 或費用。

**證據與限制。** exact baseline/candidate 合成比較維持正常進度相同；更新期間舊說明由 verified 改為 stale 並清除。到期、來源更新、session 清除、失敗停止及舊回應均有測試。W01/W02 為 N/A（無新增業務寫入）。固定 user 的現況不能證明 C02；LIVE_NOT_RUN 也不能用 fixture 取代。待補雙使用者授權映射及本週真實 Gemini run 後，才能宣稱完整驗收。

公開證據僅含控制流程、測試結果及內容雜湊；完整合成HTTP/學業payload不發布。請執行已提交的fixture runner重現細節。這是資料省略，不是以摘要冒充真實Gemini或跨user通過。
