# Week 06 — 畢業缺項說明與評估修正

## 範圍

這條子流程延續學生個人安排系統的畢業進度功能。原本的畢業計算維持唯讀；新增功能只在使用者要求時，讓 OpenAI 根據後端重新計算的進度產生結構化說明。

- 基線：`codex/week05-graduation-langgraph`，commit `13be93782ef44e08886f86afffedd7f8fc72333d`。
- 匯入來源：`codex/week06-graduation-explanations`。
- 規則版本仍是 `nutn-csie-115-mvp-v1`，尚未遷移至目標 v2。
- 固定測試使用者仍不是正式登入，不宣稱完成正式學生隔離或部署。

## 流程與資料契約

1. 後端讀取目前使用者、啟用規則與畢業進度。
2. 缺規則或檢查項目不可用時，直接回傳基本進度與原因，不呼叫模型。
3. OpenAI 產生結構化說明 A。
4. 程式核對每個 claim 的數字、`null`、狀態、來源、覆蓋範圍與 action。
5. A 未通過時，將 A 與錯誤代碼交給 OpenAI 產生 B。
6. B 使用同一規準重評；仍不合格則 `REVISION_LIMIT` 並回退基本進度。

模型只取得規則版本、總學分、整體狀態與各 check 的 ID、名稱、門檻、採計值、缺額、單位及狀態。模型不取得姓名、學號、user ID、逐筆修課、成績、原始文件、登入憑證或寫入工具。

## API 與前端

- `GET /api/v1/graduation-progress`：保留原行為，載入頁面不呼叫模型。
- `POST /api/v1/graduation-explanation`：不接受瀏覽器提供的學分；後端重新計算後才呼叫模型。
- provider 失敗時回傳 `status=fallback` 與基本進度。
- `GraduationProgress.jsx` 顯示 workflow run ID、說明狀態及回退訊息。
- `vite.graduation.config.js` 只在本機把 `/api/v1` 代理到後端。

## 驗收與限制

匯入證據包含正常 fixture、非法輸入、provider 失敗、checksum 損壞、A/B 重評及資料庫不變。歷史 `docs/week06/evidence/live.json` 明確標示 `LIVE_NOT_RUN`；fixture 不是模型自然犯錯或真實 OpenAI 證據。

本機合成驗收：

```bash
./.venv/bin/python backend/week06_acceptance.py
```

真實 OpenAI 補驗證：

```bash
./.venv/bin/python backend/week06_acceptance.py --live
```

只有實際 OpenAI 呼叫與同規準通過才可記為 `LIVE_PASS`。不得把金鑰寫入程式、文件或 Git。
