# ADR — 智慧複習排程採 Prompt Chaining Gate

## 狀態

Accepted for candidate validation。Case 1 真實 Gemini 尚未執行，因此不宣稱 Week 06 已完整 LIVE_PASS。

## 問題

原本已有 preview_study_plan 與 Gemini tool-use runner，但沒有把「自然語言抽取 → 中間資料驗證 → scheduler → 最終摘要」明確做成可檢查的相依階段。若模型抽取出錯，而程式直接把資料交給下游，控制與失敗位置不清楚。

## 決策

只重構智慧複習排程的 read-only preview 子流程為 Prompt chaining：

1. 輸入預檢。
2. Gemini 抽取固定 request contract。
3. deterministic Gate 驗證必要欄位、日期、分鐘數、可用時段與 busy interval。
4. Gate 通過後才呼叫既有 preview_study_plan。
5. 摘要階段只能看到已驗證的 tool result。

Gate reject 時，business tool 與 summary 必須 0 次。

## 保留的既有責任

- scheduler_v1 的排程演算法。
- preview_study_plan 的 read-only 業務終點。
- Week 04/05 的寫入確認與 request_id 安全規則。
- 錯誤必須明示，不用舊結果或假結果補成功。

## 替代方案

### Routing

目前這個改動只處理「複習排程預覽」單一意圖，沒有兩個需要各自後續處理的專用分支；因此本週不為了展示而硬加 router。

### Parallelization

抽取、驗證、scheduler 與摘要彼此有相依，不能安全並行。

### Orchestrator–workers

本案例的子任務清單固定，沒有必要讓模型動態產生 worker 清單。

### Evaluator–optimizer

目前問題是中間資料與下游控制，不是「同一份草稿未達品質規準後需要有限修訂」。

## 代價

- 多一層 workflow trace 與 Gate 程式。
- 正常 Live 需要兩次 Gemini 文字呼叫（抽取與摘要），模型請求數比單次工具提案更多。
- token usage、延遲與費用若未實際量測就標示未取得，不推定更省。

## Scaffold／資訊決策

系統保存清理後的抽取結果、Gate 結果、tool result、summary 與停止原因；不保存 API key，也不要求或記錄隱藏推理。摘要只收到已驗證 tool result，避免把無關歷史或未通過 Gate 的資料重新送入模型。

## 停止

- 空輸入：invalid_input
- Provider extraction failure：provider_failure
- Gate reject：gate_rejected
- Tool failure：tool_failure
- Summary provider failure：provider_failure_after_tool
- 成功：completed

所有失敗都有有限出口，不自動無限重試。

## 回退

本週只新增 Week 06 檔案，不修改 backend/scheduler.py 或 backend/week04_tools.py。回退時停止使用 backend/week06_chaining.py，直接回到原 preview_study_plan／既有 runner。
