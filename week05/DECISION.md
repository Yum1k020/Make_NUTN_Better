# Week 05 一頁重構決策

## 決策狀態

PENDING_CI — 候選程式已接回 Week 04 的真實 preview/save 工具；待 GitHub Actions 實際安裝 LangGraph 並跑完同案例驗收後，才把狀態改成 ADOPT 或 KEEP_BASELINE。

## 替換範圍

原本 week04/write_demo.py 自己負責：

    preview → input(YES) → save

Week 05 候選把「等待與接續」交給 LangGraph：

    preview node
      ↓
    approval node → interrupt
      ↓ same thread_id
    Command(resume=decision)
      ├─ YES → save node
      └─ 其他 → reject node

SQLite checkpointer 只保存流程狀態；真正的 study session 仍由 Week 04 save_study_plan 寫入。

## 框架接手的工作

- StateGraph 的節點與路由。
- interrupt 暫停。
- thread_id 對應 checkpoint。
- Command(resume=...) 接續同一流程。
- SQLite checkpoint 讓 runtime 關閉後仍可恢復。

## 應用仍保留的責任

- scheduler_v1 的可用時間與衝突規則。
- preview_study_plan 不修改資料。
- 只有精確字串 YES 才算確認。
- save_study_plan 的 request_id、fingerprint 與 replay 防重複。
- 真正寫入 study_sessions.json 的副作用。
- 任何錯誤都必須明示，不用假成功補結果。

## 預期收益

原版的業務函式完全保留，不需要把排程規則改寫進框架；候選只把跨請求的等待／接續與 checkpoint 交給 LangGraph。這正好是目前手刻流程最重複、也最容易在未來 UI/API 化時自行維護出錯的部分。

## 新增成本

- 新增 langgraph 與 langgraph-checkpoint-sqlite 相依。
- 新增 State ↔ 原工具 dict 的轉接。
- checkpoint schema／套件升級需要測試。
- SQLite 適合本機與小型展示，不代表正式多人環境的 production storage。

## 採用判準

只有下列條件全部通過才採用候選：

- 同 fixture preview 完全相同。
- 暫停時 0 筆寫入。
- 拒絕 0 筆寫入。
- runtime 重建後可接續同一 thread。
- YES 後只建立 3 筆 session。
- 同 request_id 重送仍只有 3 筆。
- 小寫 yes 不可繞過精確確認。
- 原 Weeks 02–04 regression tests 不退步。

若任一安全條件失敗，保留 Week 04 原版。

## 回退

候選是新增檔案，沒有刪除或覆蓋 week04/write_demo.py。回退只要停止使用 backend/week05_langgraph.py；原版流程仍可獨立執行。
