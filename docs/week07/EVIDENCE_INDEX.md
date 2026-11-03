# Week 07 Evidence Index

| 證據 | 位置 | 狀態 |
|---|---|---|
| Memory implementation | backend/week07_memory.py | implementation SHA 72380961e4d096b8d334d87d53546f750d4292ac |
| Route A tests | tests/test_week07_memory.py | PASS |
| Offline comparison | week07/evidence/offline_comparison.json | offline_all_pass=true |
| Gemini Live runner | week07/live_memory.py | 已實作 |
| Live evidence | week07/evidence/W07-LIVE-*.json | LIVE_NOT_RUN |
| ADR | docs/week07/ADR.md | Accepted offline |
| Baseline / Candidate | docs/week07/COMPARISON.md | 已補實測 |

## CI Evidence

- Run ID：40618188523
- Job ID：122585522782
- Pytest：31 passed, 1 xfailed
- Artifact ID：12786022642
- Workflow：success

## 共同與 Route A 案例

- C01：PASS；確認 v1 後，新 session 讀回 60 並完成 180 分鐘 preview。
- C02：PASS；跨 user forbidden。
- A 更正：PASS；60 → 30，讀 v2。
- A 撤回：PASS；撤回後 not_found。
- W01：PASS；未確認不寫。
- W02：PASS；同 request_id replay，不增加 records。
- Expiry：PASS；到期排除。
- Illegal value：PASS；有限停止，沒有檔案副作用。
- LIVE：LIVE_NOT_RUN；需本週真實 Gemini。

## 清理

Evidence 只含合成 user id、來源 id、版本、工具結果與 provider error。不得提交 API key、token、ADC JSON、.env 或真實個資。
