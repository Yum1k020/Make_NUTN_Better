# Week 07 Baseline vs Memory Candidate

Baseline SHA：9e2407a9a9a160b5ca5b51fc6e4a090ba077768e

| 比較項目 | Baseline | Route A candidate |
|---|---|---|
| 新 session 的 session_minutes | 必須重新提供 | request 缺值時可讀有效偏好 |
| 偏好來源 | 無持久偏好來源 | source_type + source_id |
| owner 隔離 | N/A | 另一 user forbidden |
| 更正 | N/A | v1 superseded，讀 v2 |
| 撤回 | N/A | revoked 後 not_found |
| 到期 | N/A | expires_at 後不回填 |
| 未確認寫入 | N/A | confirmation_required，0 write |
| 同 ID 重送 | N/A | replayed=true，0 duplicate |
| 原 scheduler | scheduler_v1 | 不修改 |
| 業務終點 | study-plan preview | 相同 |
| 真實 Gemini | 本週 baseline 不另跑 | LIVE_NOT_RUN，須私有環境執行 |

## 三層比較

1. 檢索是否讀對：只回 owner 自己、目前有效、未過期、未撤回的最新版。
2. 回答是否用對：只有 request 缺 session_minutes 時補記憶；當前明確輸入優先。
3. 任務是否完成：仍呼叫原 preview_study_plan，偏好不取代 busy interval、exam date 或其他業務資料。

calls、tokens、latency 只在真實 Live 執行後報告；未量測不推定。
