# Week 09 上下文優化短紀錄

## 方法與改動位置

我使用 **Few-shot Prompting**，接在既有 `Study Load Review Expert` 的 context。Baseline 保留 Week 08 指令；Candidate 加入 insufficient、concentrated、balanced 三個示範。實作位置是 `backend/app/study_agent_openai.py`，同案例比較由 `POST /api/v1/study-agent/context-comparison` 提供，React「智慧學習」頁可直接操作。

## 同一案例兩版輸出

固定案例、deterministic plan、模型與評估規則都相同，只切換 context version：

- Baseline：`week08-instruction-v1`
- Candidate：`week09-few-shot-v1`

離線注入證據在 `week09/evidence/offline_comparison.json`；真實模型兩版結果需由私有環境操作 UI 產生，目前標示 `LIVE_NOT_RUN`。

## 一到兩句觀察

離線結果證明同一案例的兩版確實走同一 plan 與同一 evaluator，且 Candidate context 已接回原前後端入口；但離線注入不能證明模型品質真的提升。真實模型若 Baseline 與 Candidate 都通過，這一案例也只能說「沒有退步」，不足以宣稱整體優化成功。
