# Week 07 — 兩種受限記憶與有效性控制

整合後的專案保留兩條 Week 07 子流程。智慧學習保存一筆使用者明確確認的偏好；畢業進度不長期保存 AI 說明，而是用 TTL、來源指紋與工作階段 scope 限制衍生說明的有效期。

| 子流程 | 記憶內容 | 保存位置 | 主要安全控制 |
| --- | --- | --- | --- |
| 智慧學習偏好 | `study_session_minutes` | Flask 後端 SQLite | 明確確認、owner、版本、30 天到期、撤回、冪等 |
| 畢業說明有效性 | 說明、來源指紋、run ID、300 秒期限 | 畢業頁記憶，不寫 localStorage 或長期資料表 | TTL、來源重查、scope、非同步世代檢查、清除 |

## 智慧學習的已確認偏好

- 只保存 15–240 分鐘的 `study_session_minutes`，不保存對話、私人行程、考試日期、prompt 或 API key。
- 使用者按「確認並保存」才寫入；本輪明確輸入永遠優先。
- 讀回值只預選每次安排時長，排程仍重新檢查課表、私人行程與本次需求。
- 相同 operation ID 重送不重複產生副作用；舊版本寫入、跨 user、未確認與非法值都拒絕。

程式入口：`backend/app/study_memory.py`、`frontend/src/lib/studyMemoryClient.js`、`frontend/src/components/StudyMemoryPanel.jsx`。`backend/week07_memory.py` 保留為課堂離線比較 runner，不再是網站的持久化入口。

詳見 [`adr-001-confirmed-study-preference.md`](adr-001-confirmed-study-preference.md) 及 [`week07/evidence/offline_comparison.json`](../../week07/evidence/offline_comparison.json)。

## 畢業說明的 TTL 與來源更新控制

- 說明自伺服器讀取來源開始最多有效 300 秒，重查不延長期限。
- 來源指紋包含畢業進度與規則 digest；生成前後都重新核對。
- 來源更新、生成期間到期或重查失敗時，不顯示舊說明。
- 頁面每 15 秒及重新取得 focus/visibility 時重查；這是輪詢，不是即時推播。
- 新工作階段、導覽離開或重新整理會丟棄頁面記憶，舊非同步回應不得復原已清除內容。
- session cookie 的 scope 不是登入身分，正式跨 user 授權仍未完成。

程式入口：`backend/app/graduation_validity.py`、`backend/app/graduation_explanation_api.py`、`frontend/src/lib/graduationMemory.js`、`frontend/src/components/GraduationProgress.jsx`。

完整說明見 [`GRADUATION_MEMORY_SCOPE.md`](GRADUATION_MEMORY_SCOPE.md)、[`TEST_MATRIX.md`](TEST_MATRIX.md) 與本目錄證據。

## 安全與驗證界線

- 智慧學習偏好已與個人安排統一存入 SQLite 並使用交易；正式部署仍需登入、server-side user ID、多程序併發與備份政策。
- 畢業說明到期只停止新使用，不保證刪除截圖、第三方日誌或備份。
- 兩條流程都保留原本規則計算與失敗 fallback。
- 匯入的畢業說明 live evidence 為 `LIVE_NOT_RUN`，正式跨 user 案例為 `NOT_RUN`。
- 沒有私人 provider 憑證時不得宣稱 live pass，也不得提交 `.env`、token、ADC JSON 或真實個資。
