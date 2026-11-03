# Week 06 Evidence Index

| 證據 | 位置 | 狀態 |
|---|---|---|
| Workflow 程式 | backend/week06_chaining.py | implementation SHA 0fb360c4b98ff9fe59aac31dc7ac499d2cb10321 |
| Gemini Live client | week06/gemini_client.py | 已實作 |
| Live runner | week06/live_chaining.py | 已實作；Case 1 尚未真實執行 |
| 四條控制測試 | tests/test_week06_chaining.py | PASS in CI |
| 同案例 offline comparison | week06/evidence/offline_comparison.json | offline_all_pass=true |
| Case 1 normal main flow | week06/evidence/W06-LIVE-*.json | LIVE_NOT_RUN |
| ADR | docs/week06/ADR.md | 已完成 |
| Before / After | docs/week06/COMPARISON.md | 已補實測結果 |

## CI

- Run ID：39535318301
- Job ID：119010509951
- Pytest：23 passed, 1 xfailed
- Artifact ID：12316908293
- Workflow conclusion：success

## 四條案例狀態

1. 正常主流程：LIVE_NOT_RUN。課堂要求真實 Gemini，CI 無私人 key，不以 fixture 冒充。
2. 非法輸入：PASS_OFFLINE。空輸入在 extractor 前停止，model/tool/summary 均 0。
3. Provider failure：PASS_INJECTED。錯誤來源明示，stop_reason=provider_failure，tool 0。
4. Chaining 邊界：PASS_OFFLINE。抽取後 Gate 拒絕，preview tool=0、summary=0。

## 清理規則

可提交：固定合成 request、stage status、actual tool result、Gate errors、停止原因、provider HTTP error 文字、run ID。

不可提交：.env、API key、ADC JSON、token、個資、隱藏推理。

## LIVE 狀態定義

- LIVE_NOT_RUN：缺設定或尚未真正送出本週 Gemini 請求。
- LIVE_FAIL：真的送出請求，但 provider、模型輸出或 workflow 失敗。
- LIVE_PASS：本週正常主流程真的完成 Gemini extraction → Gate → tool → Gemini summary，且業務終點正確。
