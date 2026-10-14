# Week 05 Acceptance Matrix

同一份輸入：`tests/fixtures/week04_plan.json`。

| 案例 | 預期 | 實際 |
|---|---|---|
| 原版 vs 候選 preview | 完全相同 | PASS — `same_preview=true` |
| interrupt 前 | `awaiting_confirmation`；0 筆寫入 | PASS — `paused_before_write=true` |
| decision=NO | rejected；0 筆寫入 | PASS — 測試通過 |
| runtime 關閉後 decision=YES | 從同 thread 接續；saved | PASS — `cross_runtime_resume_saved=true` |
| 同 request_id 新 thread 重送 | `replayed=true`；總 session 仍 3 | PASS — `idempotent_replay=true` |
| decision=yes | rejected；不可寫入 | PASS — `lowercase_yes_rejected=true` |
| Weeks 02–04 regression | 不退步 | PASS — pytest `19 passed, 1 xfailed`（含 Week 05） |

## CI Evidence

- GitHub Actions run：`38504073925`
- Job：`115657405988`
- Commit：`10280619d102c6b24c1e802d514a0236fde89241`
- Workflow conclusion：`success`
- Week 05 comparison：`all_pass=true`
- Candidate 最終寫入：3 sessions
- Evidence artifact ID：`11867635421`
- Repo evidence：`week05/evidence/week05_comparison.json`

本週替換的是人工確認的 pause/resume orchestration，所以此驗收本身模型呼叫為 0 次；不把 Week 04 的 Gemini LIVE_FAIL 歷史結果冒充本週 Live。
