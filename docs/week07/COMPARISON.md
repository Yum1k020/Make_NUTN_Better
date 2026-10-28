# Week 07 Baseline vs Memory Candidate

Baseline SHA：9e2407a9a9a160b5ca5b51fc6e4a090ba077768e

Implementation SHA：72380961e4d096b8d334d87d53546f750d4292ac

| 比較項目 | Baseline | Route A candidate |
|---|---|---|
| 新 session 的 session_minutes | 必須重新提供 | 缺值時讀有效偏好 |
| 偏好來源 | 無持久偏好來源 | source_type + source_id |
| owner 隔離 | N/A | PASS：另一 user forbidden |
| 更正 | N/A | PASS：v1 superseded，讀 v2 |
| 撤回 | N/A | PASS：revoked 後 not_found |
| 到期 | N/A | PASS：expires_at 後不回填 |
| 未確認寫入 | N/A | PASS：confirmation_required，0 write |
| 同 ID 重送 | N/A | PASS：replayed=true，0 duplicate |
| 原 scheduler | scheduler_v1 | 不修改 |
| 固定業務終點 | study-plan preview | PASS：仍排滿 180 分鐘 |
| 真實 Gemini | 本週 baseline 不另跑 | LIVE_NOT_RUN |

## CI

- Run 40618188523 → success
- Job 122585522782
- 31 passed, 1 xfailed
- offline_all_pass=true
- Artifact 12786022642

## 三層結果

1. 檢索是否讀對：owner、最新版、未撤回、未過期皆受控。
2. 回答是否用對：只有本輪缺 session_minutes 時才使用記憶；明確輸入優先。
3. 任務是否完成：仍使用原 preview_study_plan；偏好不取代 busy interval、exam date 或其他業務規則。

calls、tokens、latency 只在 Week 07 真實 Live 後報告；未量測不推定。
