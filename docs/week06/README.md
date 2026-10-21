# Week 06 — Prompt Chaining Workflow Increment

## 一句話交付

我們在原專案的「智慧複習排程預覽」子流程，用 Prompt chaining 修正「模型抽取結果若未檢查就可能直接進 scheduler」的控制問題；程式、四條案例、前後比較、ADR 與證據索引都從本頁連入。

## 原題目與業務終點

原題目仍是「學生個人安排系統」。本週只改智慧學習的一段：

    使用者自然語言
        ↓
    抽取排程條件
        ↓
    驗證 Gate
        ↓
    preview_study_plan
        ↓
    摘要

業務終點仍是 read-only 複習排程預覽。本 workflow 不寫入 study session，不改畢業規則，也不替換整套 agent。

## 為什麼選 Prompt chaining

這一段有明確相依：scheduler 只能吃已驗證的結構化資料；摘要也只能使用實際 tool result。若把抽取、驗證與工具呼叫混在一起，錯誤中間資料可能繼續往下游傳。

候選明確拆成：

    Stage 0  input precheck
        ↓
    Stage 1  Gemini extraction
        ↓
    Gate     deterministic validation
        ├─ reject → STOP
        ↓ pass
    Stage 2  preview_study_plan
        ↓
    Stage 3  Gemini summary
        ↓
    answer_ready

核心斷言：Gate reject 後，preview tool 與 summary 都必須是 0 次。

## 程式入口

- backend/week06_chaining.py：workflow 與 Gate。
- week06/gemini_client.py：真實 Gemini extraction／summary client。
- week06/live_chaining.py：正常主流程 Live runner。
- tests/test_week06_chaining.py：本週離線控制測試。
- week06/run_acceptance.py：同 fixture 的 baseline／candidate 比較。

## 執行

離線回歸與比較：

    py -m pytest -c pytest_agentic.ini -v
    py -m week06.run_acceptance

真實 Gemini 正常主流程：

    $env:GEMINI_API_KEY="你的私人 key"
    $env:GEMINI_MODEL="你的可用模型"
    py -m week06.live_chaining

不要把 .env、API key、ADC JSON、token 或個資提交到 repo。

## 狀態

CI 可以驗證程式控制、非法輸入、注入 provider failure 與 Gate 邊界，但沒有私人 Gemini key。依課堂規則，fixture 不能冒充正常主流程的真實 Gemini，因此 Case 1 在真正執行 week06.live_chaining 前維持 LIVE_NOT_RUN。

- Case 1 正常主流程：LIVE_NOT_RUN
- Case 2 非法輸入：由 CI 驗證
- Case 3 Provider failure：注入測試，與真實 provider failure 分開
- Case 4 Chaining Gate 邊界：由 CI 驗證

前後比較見 COMPARISON.md，架構決策見 ADR.md，證據索引見 EVIDENCE_INDEX.md。
