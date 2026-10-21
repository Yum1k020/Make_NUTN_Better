# Week 06：智慧學習 Prompt Chaining Workflow

## 一句話交付

我們在原專案的「智慧學習」子流程，用 Prompt chaining workflow 修正排程、安全檢查與 Agent 說明之間沒有明確交接與停止證據的問題，證據在本文件、[`adr-001-study-plan-prompt-chaining.md`](adr-001-study-plan-prompt-chaining.md) 與自動測試。

## 範圍與版本

- 原題目：學生個人安排系統。
- 原使用者故事：學生設定考試日期、複習時數與可用時段，系統避開課程及私人行程產生學習計畫。
- 業務終點：產生可檢查、可手動調整的複習時段與說明，不自動寫入校務系統。
- Baseline SHA：[`0128b36`](https://github.com/Yum1k020/Make_NUTN_Better/commit/0128b36)。
- Candidate SHA（程式與測試）：[`f572397`](https://github.com/Yum1k020/Make_NUTN_Better/commit/f572397)。
- 本週只改「智慧學習」的一段子流程，不更換 React、Vite、OpenAI Agents SDK 或其他功能。

## 原流程與缺口

Baseline 會依序驗證請求、產生規則排程、呼叫 Agent，但沒有一個可觀察的 workflow 契約：

- 排程完成後，沒有獨立 Gate 重新核對日期、允許時段、衝突、時數加總與識別碼。
- 失敗時只看到一般錯誤，無法從 UI 辨識停在哪一階段。
- 無法直接證明 Gate 拒絕後 Agent 階段是 0 次。

## 選定 Workflow

採用 **Prompt chaining**，因為這段流程有固定的相依順序，後一階段必須使用前一階段已驗證的輸出：

```text
需求驗證
  -> 規則排程
  -> 衝突與完整性 Gate
  -> Agent 說明
```

| 階段              | 輸入                                 | 輸出                                               | 放行條件                        |
| ----------------- | ------------------------------------ | -------------------------------------------------- | ------------------------------- |
| 需求驗證          | 日期、時數、可用時段、課程與私人行程 | 正規化請求                                         | Schema 無問題，考試日晚於起始日 |
| 規則排程          | 正規化請求                           | `sessions`、`scheduledMinutes`、`remainingMinutes` | 規則引擎成功回傳                |
| 衝突與完整性 Gate | 請求與排程                           | 問題清單                                           | 0 項問題                        |
| Agent 說明        | Gate 通過的排程                      | structured output 說明                             | Provider 成功且輸出通過 schema  |

## Scaffold 與強制停止

| Stop reason          | 停止點            | 後續行為                       |
| -------------------- | ----------------- | ------------------------------ |
| `INVALID_REQUEST`    | 需求驗證          | 不執行排程與 Agent             |
| `RULE_ENGINE_FAILED` | 規則排程          | 不進入 Gate 與 Agent           |
| `PLAN_GATE_REJECTED` | 衝突與完整性 Gate | 不呼叫 Agent，不採用不安全排程 |
| `AGENT_STAGE_FAILED` | Agent 說明        | 有限停止，前端保留原本規則排程 |

Workflow 每次只允許一次 Agent 說明嘗試，不在本層無限重試。Trace 只保留階段、狀態、計數、公開 stop reason 與 run ID；不保存私人行程內容、API key、完整 prompt 或模型內部推理。

## 四條必備案例

| #   | 案例               | 預期                                                   | 實際                                             | 狀態與證據                                                             |
| --- | ------------------ | ------------------------------------------------------ | ------------------------------------------------ | ---------------------------------------------------------------------- |
| 1   | 正常主流程         | 真實 Agent 呼叫成功，四階段通過，保留 360 分鐘規則排程 | 3 個時段、360 分鐘、尚缺 0；四階段皆 `completed` | `LIVE_PASS`；2026-10-21；`week06-697e30d1-b978-47ba-b6a4-27b23aa55d52` |
| 2   | 非法輸入           | 拒絕同日起始與考試日，不沿用舊結果                     | `INVALID_REQUEST`；planner 0 次、Agent 0 次      | `TEST_PASS`；`week06 case 2`                                           |
| 3   | Provider 失敗      | 只嘗試一次，如實停止並保留原規則結果                   | 注入失敗後回報 `AGENT_STAGE_FAILED`，attempt 1   | `TEST_PASS`；`week06 case 3`；注入測試與實測分開                       |
| 4   | Chaining Gate 邊界 | 排程與課程重疊時 Gate 拒絕，Agent 0 次                 | `PLAN_GATE_REJECTED`；下游 0 次                  | `TEST_PASS`；`week06 case 4`                                           |

本流程沒有建立保留、付款或遠端寫入，因此不需要第 5 條寫入重送案例。

## Before / After 比較

| 比較欄位       | Baseline `0128b36`                                  | Candidate `f572397`                                                       |
| -------------- | --------------------------------------------------- | ------------------------------------------------------------------------- |
| 版本與控制     | Schema 與規則函式存在，但沒有統一 workflow trace    | 四階段 Prompt chaining，階段契約與 Gate 可檢查                            |
| 固定任務與終點 | 6 小時複習規劃，排程可調整                          | 相同輸入、fixture、規則引擎與業務終點                                     |
| 成功與安全     | Baseline 測試 12/12 通過；Agent 失敗時前端 fallback | Candidate 測試 16/16 通過；Gate 拒絕後 Agent 0 次；真實 smoke `LIVE_PASS` |
| 呼叫與代價     | 未量測 token 與延遲                                 | 一次 Agent 階段嘗試；CLI 端到端約 17 秒；token usage 未取得               |
| 證據           | 原規則測試與 Week 04 文件                           | workflow run ID、四階段 trace、四條案例與 UI                              |

本次不宣稱省 token、省費用或提高排程正確率；改善的是「控制邊界與可觀察證據」。

## 程式與執行

- `frontend/server/studyPlanWorkflow.js`：需求 schema、四階段 workflow、Gate、stop reason 與安全 trace。
- `frontend/server/studyAgent.js`：把 Agents SDK 說明放在 Gate 之後。
- `frontend/server/studyAgentMiddleware.js`：將公開錯誤碼與 workflow trace 回傳給前端。
- `frontend/src/components/StudyPlanner.jsx`：顯示階段、結果、stop reason 與 run ID。
- `frontend/tests/studyPlanWorkflow.test.js`：四條必備案例。

```bash
cd frontend
npm test
npm run build
npm run format:check
npm run agent:smoke
```

## 清理後證據索引

| 證據階段    | 位置                                                       | 可核對內容                                |
| ----------- | ---------------------------------------------------------- | ----------------------------------------- |
| 請求        | `studyPlanWorkflow.js` 的 `studyPlanRequestSchema`         | 只接受規劃需要的欄位                      |
| Actual call | `studyAgent.js` 的 `runStudyPlanWorkflow()` / `runAgent()` | Agent 只在 Gate 通過後執行                |
| 檢查／確認  | `verifyStudyPlan()`                                        | 日期、時段、衝突、時數、重複 ID           |
| 結果        | `workflow.stages` 與 `stopReason`                          | 階段成功、拒絕或失敗                      |
| 回送        | `studyAgentMiddleware.js` 與 `studyAgentClient.js`         | 成功或安全錯誤格式                        |
| 摘要        | `StudyPlanner.jsx` 的 workflow trace                       | 畫面可見的階段、計數、stop reason、run ID |

## 已知問題與補驗證

- `LIVE_PASS`：2026-10-21 使用合成課名、固定日期與空的私人行程完成一次真實 OpenAI Agent 請求。
- 這個 `LIVE_PASS` 只證明當時本機開發環境與 API 可用，不證明正式部署、校務系統或長期可用性。
- Vite middleware 仍是本機原型；正式部署前要移至受控後端。
- 當網路、key 或 provider 失敗時，UI 會保留本機規則排程；不把該情況說成 Agent 完成。
- `.env.local`、API key、token、個資與模型內部推理均不在 Git 交付範圍。
