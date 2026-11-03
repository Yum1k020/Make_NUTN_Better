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


---

## 畢業功能線文件（原始分支內容）

# ADR｜以受限說明與同規準重評改善畢業進度

日期：2026-10-21（Asia/Taipei）｜狀態：實作候選；真實模型驗收待完成。

**問題。** week05 已將畢業計算分成可觀察的 LangGraph 階段，前端仍顯示固定示範資料。學生需要知道缺什麼與下一步，但模型若自由改寫，可能把未知當零、規劃算成已取得、漏來源或誇大正式認證。

**選擇。** 保留原有計算與 checksum 驗證，在唯讀進度之後新增 Evaluator–optimizer。Gemini 產生結構化說明 A；程式以數字、狀態、來源、覆蓋與可用 action 檢查；未通過才將 A 與錯誤代碼回送給 Gemini 產生 B，同規準重評。最多兩稿，錯誤即回退基本進度。

**資訊與支架決策。** 模型只取得去識別的彙整 check，不取得成績、原始修課或寫入工具。輸出限制為已知 claims 與 action，中文顯示文字由已核對 claims 呈現。這讓驗收能完整覆蓋每個會出現在畫面的事實，也避免靠關鍵字黑名單聲稱檢查所有自由文字。代價是說明語氣較固定，模型目前主要負責排列重點與依回饋修正，不提供任意個人化長文。

**替代方案。** 純 Chaining 加 Gate 更便宜，但無模型回饋修正；Parallelization 在既有學分分配與條件檢查之間有相依，沒有先證明並行收益；動態派工與 ReAct 會增加工具權限與測試面，這個子流程不需要；模型判定畢業資格難以維持可重現採計，因此未採用。

**代價與量測。** 每次說明最多兩次模型請求，基本進度仍零次模型呼叫。新增 schema、評估器、接頭與測試維護成本。實際 fixture 只能證明控制行為；無 live 用量就不宣稱模型品質提升、節省費用或效能改善。

**停止與回退。** 缺規則或設定不呼叫；provider 失敗即停，不自動重試；B 仍未達標為 REVISION_LIMIT。資料庫讀取交易在外部請求前釋放。新 POST 不寫業務資料。撤回程式提交即可回復，不做資料遷移；原 legacy 開關保留。

**整合。** 新模組獨立；共用後端僅在既有註冊點增加兩行。前端只改畢業頁，新 CSS 與代理 config 獨立。分支合併結果及原有衝突列在證據，不能以「檔案不同」直接推定功能相容。

**驗收範圍。** 四類案例、前後事實等價、未知保留、錯誤回退、資料庫不變與 A/B 可觀察性。尚待真實 Gemini 主流程；正式登入、多使用者隔離、規則 v2 遷移與當期選課建議不屬本次完成範圍。
