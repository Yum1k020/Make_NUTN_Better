# Week 05 Acceptance Matrix

同一份輸入：tests/fixtures/week04_plan.json。

| 案例 | 預期 | 實際 |
|---|---|---|
| 原版 vs 候選 preview | 完全相同 | PENDING_CI |
| interrupt 前 | awaiting_confirmation；0 筆寫入 | PENDING_CI |
| decision=NO | rejected；0 筆寫入 | PENDING_CI |
| runtime 關閉後 decision=YES | 從同 thread 接續；saved | PENDING_CI |
| 同 request_id 新 thread 重送 | replayed=true；總 session 仍 3 | PENDING_CI |
| decision=yes | rejected；不可寫入 | PENDING_CI |
| Weeks 02–04 regression | 不退步 | PENDING_CI |

實際證據由 python -m week05.run_acceptance 產生 JSON；GitHub Actions 也會上傳同一份 JSON artifact。不要在執行前手填 PASS。
