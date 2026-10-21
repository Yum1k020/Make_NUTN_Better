# Week 06 Before / After

固定案例沿用 tests/fixtures/week04_plan.json，不改輸入、scheduler 或業務終點。

| 比較欄位 | Baseline | Candidate |
|---|---|---|
| 版本 | e71192abdc329446fbd28414cda14c31d2f310c4 | implementation SHA 0fb360c4b98ff9fe59aac31dc7ac499d2cb10321 |
| 控制方式 | structured request 可直接進 preview tool | extract → Gate → preview tool → summary |
| 業務終點 | read-only study-plan preview | 相同 |
| scheduler | scheduler_v1 | 相同 |
| 固定 fixture preview | 180 分鐘、remaining 0、3 sessions | PASS，與 baseline 完全相同 |
| Case 1 真實 Gemini | 本週未另做 baseline live | LIVE_NOT_RUN |
| Case 2 非法輸入 | 無本週 chaining precheck | PASS；model/tool/summary 都 0 次 |
| Case 3 provider failure | 非本週控制 | PASS_INJECTED；stop_reason=provider_failure，tool 0 次 |
| Case 4 workflow 邊界 | 無本週 Gate 斷言 | PASS；Gate reject 後 tool=0、summary=0 |
| 模型呼叫 | 不做推定 | CI 離線不呼叫；Live 成功路徑預期 extraction + summary 共 2 次 |
| tool 呼叫 | baseline preview 1 次 | Gate pass 為 1 次；reject 為 0 |
| token usage | 未取得 | LIVE_NOT_RUN，未取得 |
| latency | 未取得 | LIVE_NOT_RUN，未取得 |

## CI 實際結果

- GitHub Actions run：39535318301
- Job：119010509951
- Regression：23 passed, 1 xfailed
- offline_all_pass：true
- Evidence artifact：12316908293
- Repo evidence：week06/evidence/offline_comparison.json

## 結論

已證明候選保留原本的 preview 業務結果，並新增可拒絕 Gate、明確停止原因與下游零呼叫斷言。尚未證明的是 Case 1 的本週真實 Gemini 正常主流程；依課堂規則保持 LIVE_NOT_RUN，不用 fixture 或歷史結果冒充。
