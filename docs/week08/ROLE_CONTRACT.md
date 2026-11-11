# Week 08 Role Contract

## R1 — Study Coordinator

| 欄位 | 契約 |
| --- | --- |
| Owner | 原智慧學習主流程 |
| Input | 已驗證的完整 study-plan request |
| Model step | Tool selection、final summary |
| Allowed tool | `get_validated_study_plan` |
| Write permission | 無自動寫入；寫入仍使用原 UI／Flask 明確操作 |
| Receives | deterministic plan、bounded expert review |
| Final answer | 是 |
| Stop | schema reject、tool args mismatch、expert invalid/provider failure |

## R2 — Study Load Review Expert

| 欄位 | 契約 |
| --- | --- |
| Owner | 限定的讀書負荷檢查子任務 |
| Input | 去識別 task + sanitized sessions + remainingMinutes |
| Model step | 一次 structured review |
| Allowed tool | 無 |
| Write permission | 無 |
| Forbidden context | personalEvents 原始內容、私人地點、完整記憶、credentials |
| Output | assessment、summary、recommendations、citations |
| Return target | Study Coordinator |
| Final answer | 否 |
| Stop | 一次模型步驟；schema／facts 不一致即拒絕 |

## Shared scope

只分享完成子任務所需欄位。狀態仍由可信程式更新；專家自稱完成不代表 workflow 成功。

## Control

```text
Study Coordinator --delegate--> Study Load Review Expert
Study Coordinator <--return--- Study Load Review Expert
Study Coordinator --final-----> User
```

這是回傳式專家，不是 Handoff；active controller 不轉移。
