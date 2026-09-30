# 學生安排 API 實作進度

最後更新：2026-09-24T22:31:15.214922+08:00。

- 分支：`feature/student-planner-api-flask`。
- 起點：`d32c99b6c88eda6590111e650698e6addc0c4a8c`。沿用 Flask／SQLite／固定測試使用者。
- 狀態：19 組 baseline 功能、OpenAPI 請求文件、交易與版本保護、實測文件已完成；尚未提交或推送本次變更。
- 最後實測：252 passed、4 skipped，exit 0。含真正 HTTP 重啟持久化與寫入失敗回滾；測試使用暫存資料庫。
- 受測來源 fingerprint：`f8f56710dd5f52da6f23ec56f7fd336687c2bd832d7b138f1ebb25427ac6595d`。
- 詳細範圍、命令、逐案例及失敗歷史：[學生安排 API](../api/student-planner.md)；原始輸入／輸出：[完整證據](../api/evidence/planner-results.json)。
- 原始規格：[附件副本](../api/student-planner-spec.md)，原文預期表不直接作通過證據。
- 未執行：正式登入與雙登入使用者隔離、外部 AI 502、真實校務對照與正式畢業認證、前端串接、正式部署與壓力測試。
- 下次若繼續：先確認 `git status`；不改動根目錄原有未追蹤的 DATA_GUIDE.md 與規則 JSON。測試用的 133 學分全達標是合成資料，不能當正式課程對照。
- 啟動前執行 `./scripts/init-backend-db.sh`，再執行 `./scripts/run-backend.sh`；此次未修改開發資料庫。
- 使用者要求剩餘 token 接近 5% 時停止並記錄進度；本文件提供可接續的完成狀態，未將未執行項目標示通過。
