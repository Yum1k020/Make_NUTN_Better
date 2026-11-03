# Week 06 — Prompt Chaining Workflow Increment

## 一句話交付

我們在原專案的「智慧複習排程預覽」子流程，用 Prompt chaining 修正「模型抽取結果若未檢查就可能直接進 scheduler」的控制問題；程式差異、四條案例、前後比較、ADR 與證據索引都已放進原 repo。

## 原題目與業務終點

原題目仍是「學生個人安排系統」。本週只改智慧學習的一段：

    使用者自然語言
        ↓
    Gemini 抽取排程條件
        ↓
    deterministic Gate
        ├─ reject → STOP
        ↓ pass
    preview_study_plan
        ↓
    Gemini 摘要
        ↓
    answer_ready

業務終點仍是 read-only 複習排程預覽。本 workflow 不寫入 study session、不改畢業規則，也不替換整套 agent。

## 為什麼選 Prompt chaining

這一段的後一步依賴前一步：scheduler 只能吃通過 Gate 的結構化資料，摘要也只能使用實際 tool result。候選因此把抽取、Gate、tool 與摘要拆成可觀察階段。

核心斷言：Gate reject 後，preview tool 與 summary 都必須是 0 次。

## 程式入口

- backend/week06_chaining.py：workflow 與 Gate。
- week06/gemini_client.py：真實 Gemini extraction／summary client。
- week06/live_chaining.py：正常主流程 Live runner。
- tests/test_week06_chaining.py：本週四條控制測試。
- week06/run_acceptance.py：同 fixture baseline／candidate 比較。
- week06/evidence/offline_comparison.json：CI 後提交的清理證據。

## 實測結果

Implementation SHA：0fb360c4b98ff9fe59aac31dc7ac499d2cb10321

GitHub Actions run：39535318301

Job：119010509951

Artifact：12316908293

完整 regression：23 passed, 1 xfailed。

Offline comparison：offline_all_pass=true。

四項離線控制檢查：
- 原 preview 與 candidate preview 完全相同：PASS
- 空輸入在模型與工具前拒絕：PASS
- 注入 provider failure 有限停止且不假造結果：PASS
- Gate reject 後 preview tool=0、summary=0：PASS

原本既有的一項 xfail 仍是先前保留的 known failure，不是 Week 06 新退步。

## 真實 Gemini 狀態

課堂要求正常主流程必須是真的 Gemini，fixture 不能替代。因此目前誠實標示：

- Case 1 正常主流程：LIVE_NOT_RUN
- Case 2 非法輸入：PASS_OFFLINE
- Case 3 Provider failure：PASS_INJECTED
- Case 4 Chaining Gate 邊界：PASS_OFFLINE

真實 Gemini runner：

    $env:GEMINI_API_KEY="你的私人 key"
    $env:GEMINI_MODEL="你的可用模型"
    py -m week06.live_chaining

沒有 API key 時不宣稱 LIVE_PASS，也不要把 .env、API key、ADC JSON、token 或個資提交到 repo。

前後比較見 COMPARISON.md，架構決策見 ADR.md，證據索引見 EVIDENCE_INDEX.md。
