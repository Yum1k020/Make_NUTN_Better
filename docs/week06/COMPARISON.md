# Week 06 Before / After

固定案例沿用 tests/fixtures/week04_plan.json，不改輸入、scheduler 或業務終點。

| 比較欄位 | Baseline | Candidate |
|---|---|---|
| 版本 | e71192abdc329446fbd28414cda14c31d2f310c4 | candidate SHA：PENDING |
| 控制方式 | structured request 可直接進 preview tool | extract → Gate → preview tool → summary |
| 業務終點 | read-only study-plan preview | 相同 |
| scheduler | scheduler_v1 | 相同 |
| 正常 fixture 結果 | 180 分鐘、remaining 0 | 離線結構比較須完全相同 |
| Case 1 真實 Gemini | 本週未另做 baseline live | LIVE_NOT_RUN |
| Case 2 非法輸入 | 未設本週 chaining precheck | Candidate 必須在 model/tool 前拒絕 |
| Case 3 provider failure | Week 04 有歷史失敗，但非本週正常案例 | 本週用注入 failure 驗證有限停止；真實 failure 另列 |
| Case 4 workflow 邊界 | 無本週 Gate 斷言 | Gate reject 後 tool=0、summary=0 |
| 模型呼叫 | 不做推定 | Live 成功預期 2；CI 離線為 0 |
| tool 呼叫 | 正常 preview 1 次 | Gate pass 後 preview 1 次；reject 為 0 |
| token usage | 未取得 | LIVE_NOT_RUN，未取得 |
| latency | 未取得 | LIVE_NOT_RUN，未取得 |

## 結論

目前能證明的是：候選在離線同 fixture 下保留原 preview 結果，並新增可拒絕 Gate 與有限停止。是否完成課堂要求的「正常主流程真實 Gemini」必須以 week06/live_chaining.py 的實際 LIVE evidence 判定；在那之前不宣稱完整改善完成。
