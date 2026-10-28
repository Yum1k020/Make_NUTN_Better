# Week 07 — Agent Memory Architectures

## 本週只做一項記憶增量

原題目仍是「學生個人安排系統」，原 repo 不變。本週選 Route A：保存一個已確認偏好。

固定欄位：study_session_minutes（使用者確認的每次複習分鐘數），並保存 owner、source、version、expiry、superseded / revoked 狀態。

## 缺口與接法

Baseline SHA：9e2407a9a9a160b5ca5b51fc6e4a090ba077768e

原本智慧排程換新 session 後，session_minutes 必須重新提供。Candidate 在 request 缺少 session_minutes 時，受控讀回目前有效偏好，再接回既有 preview_study_plan；若本輪 request 已明確指定 session_minutes，當前輸入優先。

## Route A 實際驗收

GitHub Actions run：40618188523

Job：122585522782

Implementation SHA：72380961e4d096b8d334d87d53546f750d4292ac

Artifact：12786022642

完整 regression：31 passed, 1 xfailed。

offline_all_pass=true。

已驗證：
- 新 session 讀回 v1=60，原排程仍完成 180 分鐘。
- 跨 user U002 讀 U001 → forbidden。
- 更正 60 → 30 產生 v2，之後只讀 v2。
- 撤回 v2 後 → not_found。
- 未確認 → confirmation_required，0 write。
- 同 request_id 重送 → replayed=true，records 不增加。
- expiry 到期後不再回填。
- 非法分鐘數有限停止。

原本的一項 xfail 是先前保留的 known failure，不是 Week 07 新退步。

## 程式

- backend/week07_memory.py
- tests/test_week07_memory.py
- week07/run_acceptance.py
- week07/live_memory.py
- week07/evidence/offline_comparison.json

## 真實 Gemini

課堂把 LIVE 狀態獨立驗收。GitHub CI 沒有私人 Gemini API key，因此目前仍是 LIVE_NOT_RUN，不用 fixture 冒充。

私有環境執行：

    $env:GEMINI_API_KEY="你的私人 key"
    $env:GEMINI_MODEL="你的可用模型"
    py -m week07.live_memory

只有完成 Gemini proposal → human confirmation → memory write → 新 session read → 原排程 → Gemini summary 才標示 LIVE_PASS。

week07/runtime/ 已 gitignore；不得提交 API key、token、ADC JSON、.env 或真實個資。
