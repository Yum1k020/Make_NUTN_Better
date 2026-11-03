# new-develop 合併紀錄

日期：2026-11-03（Asia/Taipei）。用途：集合各功能線，作為後續共同開發基礎。此階段不執行 Flask／SQLite 全面遷移，不啟用 integrated-v2。

## 固定來源

| 來源 | Commit | 範圍 |
| --- | --- | --- |
| develop | efca82d | Flask、SQLite 與原前端 |
| feature/agentic-week07-memory-preference | 2486ef9 | 包含 Agentic Week02–07 |
| codex/frontend-week03-gate | 2b47fb4 | 證據頁、Node/OpenAI 排程與 Week06 Gate |
| codex/week07-graduation-memory-scope | cdd09df | 包含畢業 Week05–07 |

`codex/integrate-agentic-week07`（746e385）保持原樣，不是本分支的合併來源。只存在該分支的 Node 偏好面板、記憶服務與 JSON store 未納入。原 feature/c-study-scheduler 的提交已在 develop 歷史內，其後被撤回，不重新啟用 C 排程。

所有來源使用 merge 保存完整祖先歷史，不 squash、不 force push。舊功能分支先保留，不在驗證未完整前刪除。

## 衝突處理

- `.env.example` 保留 Gemini 和 OpenAI 的設定名稱。
- README 改為共同入口，舊內容保存在 source-readmes.md。
- 同名 Week06／07 文件保留排程和畢業兩部分，明確標記畢業段落。
- 排程 `docs/week06/COMPARISON.md` 更名為 `AGENTIC-COMPARISON.md`；畢業保留 `comparison.md`，避免 macOS 大小寫檔名碰撞。
- pytest 範圍放寬為 >=8,<10，以容納原 Flask 鎖定的 9.1.1。
- 新增 requirements-new-develop.txt，採 Agentic 的 LangGraph 1.2.15；畢業歷史鎖定的 1.0.3 仍保留，不可與共同需求檔同時安裝。共同 Python 環境相容性尚待驗證。
- 前端使用 vite.graduation.config.js，可同時掛載 Node Agent 與 Flask /api/v1 proxy。

## 本次驗證

| 檢查 | 結果 |
| --- | --- |
| npm ci | 成功 |
| npm test | 30 通過、0 失敗 |
| npm run build | 成功，33 modules |
| git diff --check | 通過 |
| Flask／Agentic Python 測試 | NOT_RUN：本機僅 Python 3.9.6，專案需 3.12+ |
| 真實 Gemini／OpenAI | LIVE_NOT_RUN：本次未呼叫模型 |
| 瀏覽器端到端 | NOT_RUN |

本次檢查針對合併後的前端程式；各週資料夾中的舊測試數字與錄製證據仍屬原始提交，不代表本次結果。

## 後續驗收

1. 在 Python 3.12+ 的獨立環境安裝共同需求檔，執行 pip check。
2. 分別執行 backend/tests 與 tests，確認共用 LangGraph 版本相容性。
3. 啟動 Flask 5000 與前端 5173，確認畢業頁、Node Agent 的路由與錯誤回退。
4. 後續另行實作 Flask／SQLite 統一、ADC Gemini、正式工具呼叫與資料遷移。

新分支已彙整程式，不宣稱所有頁面已使用同一後端與資料庫。
