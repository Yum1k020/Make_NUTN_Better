# Week 05 Evidence

week05_comparison.json 必須由實際執行產生：

    python -m week05.run_acceptance

內容包含同一 fixture 的 Week 04 baseline 與 LangGraph candidate 結果、跨 runtime resume、拒絕、精確 YES、idempotent replay 與總 session 數。

不得放 API key、.env、個資或 runtime SQLite。CI 會把 JSON 上傳為 artifact；通過後才更新 DECISION.md 與 ACCEPTANCE.md。
