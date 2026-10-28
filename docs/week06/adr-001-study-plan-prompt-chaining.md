# ADR-001：智慧學習採用 Prompt Chaining

- 狀態：Accepted
- 日期：2026-10-21
- Baseline：`0128b36`
- Candidate：`f572397`

## 問題

原本的智慧學習有 schema、規則排程與 Agents SDK 說明，但沒有一個明確、可觀察的執行契約來回答：現在停在哪一階段、排程是否通過獨立 Gate、Gate 拒絕後 Agent 是否真的沒有執行。

## 決策

將該子流程實作為固定四階段 Prompt chaining：

1. 需求驗證。
2. 規則排程。
3. 衝突與完整性 Gate。
4. Agent 說明。

只有前一階段成功才能進入後一階段。Gate 會重新檢查日期範圍、允許時段、課程／私人行程／複習時段衝突、時數加總與 ID 唯一性。Agent 仍只說明已驗證結果，不改寫排程。

## 替代方案

| 方案                 | 未採用理由                                              |
| -------------------- | ------------------------------------------------------- |
| 保持原狀             | 不能提供階段與停止證據，也無法直接斷言 Gate 後下游 0 次 |
| Routing              | 本使用案例不是多意圖分流，而是固定相依階段              |
| Parallelization      | 規則排程、Gate 與 Agent 說明有先後依賴，不能安全並行    |
| Orchestrator-workers | 子任務清單固定，不需要模型動態派工                      |
| Evaluator-optimizer  | 本週要解決階段交接與安全停止，不是重複修訂一份初稿      |

## 代價與後果

優點：

- 可用固定 stage ID、狀態、stop reason 與 run ID 重現執行軌跡。
- 非法輸入或 Gate 拒絕後，可以測試下游調用次數為 0。
- Agent 失敗只影響說明，不會覆蓋已經建立的本機規則排程。

代價：

- 增加一層 workflow 資料結構、錯誤類型、前後端傳遞與 UI。
- Gate 與原排程規則部分重複，未來修改排程規則時必須同步檢查驗證器。
- 本次沒有證明降低 token、費用或延遲。

## 資訊與 Scaffold 決策

Trace 只保留可驗收的外部事實：階段名稱、狀態、計數、版本、run ID 與 stop reason。私人行程只記錄筆數，不把標題、時間、地點、prompt、API key 或模型內部推理放入 trace。這個選擇讓 UI 能驗收流程，同時不擴大個資暴露範圍。

## 停止與回退

- 非法輸入：`INVALID_REQUEST`，後續階段不執行。
- 規則引擎失敗：`RULE_ENGINE_FAILED`，不使用部分結果。
- Gate 拒絕：`PLAN_GATE_REJECTED`，Agent 不執行。
- Agent 或 provider 失敗：`AGENT_STAGE_FAILED`，有限停止並保留前端原排程。
- 若新 workflow 造成回歸，可回退 commit `f572397`；資料格式與排程引擎未變更，不需要資料遷移。
