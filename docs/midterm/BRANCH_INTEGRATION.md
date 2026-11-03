# GitHub 分支整合紀錄

盤點日期：2026-11-03。目標分支：`codex/backend-persistence`。

## 遠端分支判定

| 遠端分支 | 與目前整合分支的關係 | 處理方式 |
| --- | --- | --- |
| `origin/main` | 已是目前分支祖先 | 不重複 merge |
| `origin/develop` | 已是目前分支祖先 | 不重複 merge |
| `origin/codex/integrate-agentic-week07` | 已是目前分支祖先 | 不重複 merge |
| `origin/codex/midterm-integrated-report` | 與開始本次工作時的 HEAD 相同 | 在目前分支繼續整合並推送新版本 |
| `origin/new-develop` | 有 4 個不同的平行 merge commit，但不是目前分支祖先 | 不直接 merge，避免以較舊整合覆蓋現行功能 |

## 為什麼沒有直接 merge `new-develop`

`new-develop` 的四個獨立提交整合了 Python Week 02–07、前端 Agent 與畢業 Week 05–07；目前分支已透過 `e14e76a`、`746e385` 與 `fa740a8` 等另一條 merge 歷史包含相同功能，之後又加入：

- Flask／SQLite 統一個人資料與偏好。
- `nutn-csie-115-integrated-v2` 後端啟用。
- Vertex Gemini 與 OpenAI provider adapter。
- 113／115 來源文件、期中報告與 live evidence。
- 新版測試、前端與資料遷移。

若直接把 `origin/new-develop` 的 tree 套回目前分支，會移除現行 Agent provider、115 資料、期中 PPTX／PDF、來源文件、SQLite 記憶與多個測試檔，屬功能倒退。

`new-develop` 只多出兩份歷史整合說明、舊版 comparison 檔名與舊的需求入口。這些內容記錄的是「尚未完成 Flask／SQLite 遷移」的舊狀態，不適合當成目前執行文件。整合需求已由新的 `requirements-integrated.txt` 取代。

## 已納入的功能線

- Flask 使用者、課程與 planner API。
- React 學生日程與學習規劃。
- Week 03 evidence gate。
- Week 04 tool use 與寫入安全契約。
- Week 05 LangGraph 候選流程。
- Week 06 Prompt Chaining 與畢業 evaluator-optimizer。
- Week 07 semantic preference memory 與畢業說明有效期。
- 115 畢業規則、課程目錄、修課規劃與畢業進度。
- Gemini／ADC 主 adapter 與 OpenAI 選用 adapter。
- 期中報告、測試結果與課程概念對照。

## 推送界線

本次推送目標是 `origin/codex/backend-persistence`。這代表整合分支已發布供團隊檢查，不等於已合併到 `develop` 或 `main`。若要進入受保護分支，應另外建立 Pull Request，經團隊 review 與 CI 後再合併。
