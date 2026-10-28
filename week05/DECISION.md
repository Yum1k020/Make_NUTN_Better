# Week 05 一頁重構決策

## 決策狀態

**ADOPT（採用候選）**

GitHub Actions run `38504073925` 已實際安裝 LangGraph、執行完整回歸測試與同案例驗收，結果成功。完整 pytest 為 **19 passed, 1 xfailed**；Week 05 的六項候選檢查全部為 `true`。

## 替換範圍

原本 `week04/write_demo.py` 自己負責：

    preview → input(YES) → save

Week 05 候選把「等待與接續」交給 LangGraph：

    preview node
      ↓
    approval node → interrupt
      ↓ same thread_id
    Command(resume=decision)
      ├─ YES → save node
      └─ 其他 → reject node

SQLite checkpointer 只保存流程狀態；真正的 study session 仍由 Week 04 `save_study_plan` 寫入。

## 框架接手的工作

- `StateGraph` 的節點與路由。
- `interrupt` 暫停。
- `thread_id` 對應 checkpoint。
- `Command(resume=...)` 接續同一流程。
- SQLite checkpoint 讓 runtime 關閉後仍可恢復。

## 應用仍保留的責任

- `scheduler_v1` 的可用時間與衝突規則。
- `preview_study_plan` 不修改資料。
- 只有精確字串 `YES` 才算確認。
- `save_study_plan` 的 request_id、fingerprint 與 replay 防重複。
- 真正寫入 `study_sessions.json` 的副作用。
- 錯誤明示，不用假成功補結果。

## 實測證據

- Commit：`10280619d102c6b24c1e802d514a0236fde89241`
- GitHub Actions run：`38504073925`
- Job：`115657405988`
- Framework：`langgraph==1.2.15`
- SQLite checkpointer：`langgraph-checkpoint-sqlite==3.1.2`
- Regression：`19 passed, 1 xfailed`
- 同 fixture preview：PASS
- interrupt 前 0 筆寫入：PASS
- runtime 重建後同 thread 接續並保存：PASS
- 同 request_id replay 不重複：PASS
- 小寫 `yes` 被拒絕：PASS
- 最終 candidate session 數：3
- 本替換邊界模型呼叫：0 次

完整前後結果：`week05/evidence/week05_comparison.json`。

## 實測收益

原版業務函式完全保留，不需要把排程規則改寫進框架；候選只把跨請求的等待／接續與 checkpoint 交給 LangGraph。這使未來 UI 或 API 化時，不必自己維護「停住、保存、用同一流程恢復」的通用機制。

## 新增成本

- 新增 LangGraph 與 SQLite checkpointer 相依。
- 新增 State ↔ 原工具 dict 的轉接。
- checkpoint schema／套件升級需要測試。
- SQLite 適合本機與課堂展示，不代表正式多人環境的 production storage。

## 採用理由

候選在相同 fixture 與相同 Week 04 安全規則下沒有退步，而且新增了「程序結束後仍能用同一 thread 接續」的框架能力。因為所有寫入授權與冪等仍由原應用程式控制，所以採用此局部替換，不擴大到整套系統。

## 回退

候選是新增檔案，沒有刪除或覆蓋 `week04/write_demo.py`。若 LangGraph 相依或 checkpoint 行為後續不符合需求，停止使用 `backend/week05_langgraph.py` 即可回到 Week 04 原版。
