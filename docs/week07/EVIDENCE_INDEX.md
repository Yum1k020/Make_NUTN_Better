# Week 07 Evidence Index

| 證據 | 位置 | 初始狀態 |
|---|---|---|
| Memory implementation | backend/week07_memory.py | candidate |
| Route A tests | tests/test_week07_memory.py | 待 CI |
| Offline comparison | week07/evidence/offline_comparison.json | 由 CI 產生 |
| Gemini Live runner | week07/live_memory.py | 已實作 |
| Live evidence | week07/evidence/W07-LIVE-*.json | LIVE_NOT_RUN |
| ADR | docs/week07/ADR.md | 已寫 |
| Baseline / Candidate | docs/week07/COMPARISON.md | 已寫 |

## 共同案例

- C01：確認偏好後，新 session 讀回並完成原 study-plan preview。
- C02：跨 user 不可見。
- 非法輸入：不寫入。
- 錯誤有限停止：ValueError / forbidden / not_found 均明示。
- LIVE：必須是本週真實 Gemini，與 offline 狀態分開。

## Route A 邊界

- 更正 v2。
- 撤回後不可讀。
- W01 未確認不寫。
- W02 同 request_id 不重複。
- expiry 到期排除。

## 清理

Evidence 只能含合成 user id、來源 id、版本、工具結果與 provider error。不得提交 API key、token、ADC JSON、.env 或真實個資。
