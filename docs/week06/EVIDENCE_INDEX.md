# Week 06 Evidence Index

| 證據 | 位置 | 狀態 |
|---|---|---|
| Workflow 程式 | backend/week06_chaining.py | candidate |
| Gemini Live client | week06/gemini_client.py | candidate |
| Live runner | week06/live_chaining.py | 可執行，尚未有本週真實成功紀錄 |
| 四條控制測試 | tests/test_week06_chaining.py | 待 CI |
| 同案例 offline comparison | week06/evidence/offline_comparison.json | 由 CI 產生 |
| Case 1 normal main flow | week06/evidence/W06-LIVE-*.json | LIVE_NOT_RUN |
| ADR | docs/week06/ADR.md | 已寫 |
| Before / After | docs/week06/COMPARISON.md | candidate SHA 待 CI 後補 |

## 清理規則

可提交：固定合成 request、stage status、actual tool result、Gate errors、停止原因、provider HTTP error 文字、run ID。

不可提交：.env、API key、ADC JSON、token、個資、隱藏推理。

## LIVE 狀態定義

- LIVE_NOT_RUN：缺設定或尚未真正送出本週 Gemini 請求。
- LIVE_FAIL：真的送出請求，但 provider、模型輸出或 workflow 失敗。
- LIVE_PASS：本週正常主流程真的完成 Gemini extraction → Gate → tool → Gemini summary，且業務終點正確。
