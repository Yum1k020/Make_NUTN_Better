# Week 07 證據索引

## 版本、範圍與入口

- 主說明與可重現命令：[README.md](README.md)。
- 基線：`32ec10231d70448ca43013036eec1f0869a21ce8`；候選程式：`6d97f7e8b969253bf4b3ef52df9db36959105c0a`。
- 功能及測試diff：[week07.patch](week07.patch)，只比較本週程式增量，不把第五／六週既有功能算成新增。
- GitHub分支HEAD另含證據與文件commit；測試report記錄source_commit及內容雜湊，不用文件commit冒充測試版本。

## 測試、模型與UI

| 檔案 | 可核對內容 |
|---|---|
| [focused.json](evidence/focused.json) | 39 passed、1 skipped；原Week06及Week07 HTTP／TTL／來源／scope案例，expected與actual分開 |
| [regression.json](evidence/regression.json) | 後端完整可執行回歸；實際狀態、skip原因、source hashes及環境 |
| [frontend.tap](evidence/frontend.tap) | 前端19項通過；其中11項為Week07記憶有效性案例 |
| [frontend-build.log](evidence/frontend-build.log) | 實際production build通過 |
| [format.log](evidence/format.log) | 本週修改前端檔案格式檢查 |
| [baseline.json](evidence/baseline.json) | exact baseline獨立程序的固定合成provider的控制結果與run ID（省略學業payload） |
| [candidate.json](evidence/candidate.json) | 同資料候選流程、validity、來源更新後拒絕狀態（省略學業payload） |
| [comparison.json](evidence/comparison.json) | 同任務三層品質與模型呼叫／fixture延遲，非真實成本改善 |
| [live.json](evidence/live.json) | **LIVE_NOT_RUN**，無金鑰與模型設定；normal=null，不冒充Gemini證據 |
| [ui-fixture.png](evidence/ui-fixture.png) | 實際瀏覽器畫面：合成模式、五分鐘期限、原有缺項說明 |
| [ui-check.json](evidence/ui-check.json) | 實際點擊產生合成說明、新工作階段清除的觀察；不是LIVE |
| [validation-summary.json](evidence/validation-summary.json) | 最終測試數、平台限制、待補驗證及狀態總覽 |

工具路徑：使用者按鈕 → `graduation-context` → bodyless `graduation-explanation` → schema/來源檢查 → `progress`結果放入Gemini evidence → 原A/B evaluator → I/O後再讀來源 → response validity → 前端顯示前重查 → 顯示/清除。

`baseline.json`／`candidate.json` 的provider明確為fixture，證明控制行為。真正Gemini的actual_call與usage必須透過 `--live` 另取，這次未執行。

## 邊界與未完成

- C02正式跨user：NOT_RUN。scope是瀏覽器工作階段，不是登入使用者。fingerprint對不同user資料會改變的單元測試，也不能取代實際授權驗收。
- W01/W02：N/A＋理由見TEST_MATRIX，沒有新增業務寫入工具。
- 原有4項skip，加本週C02共5項；原有三項Windows不相容pipe/select測試明確deselect。完整原因見report與validation-summary。
- 刪除範圍：僅當頁說明停止新使用；SQLite、既有trace與備份另有生命週期，沒有聲稱全域抹除。

Git API 發布時重建提交中繼資料，程式內容未改：本機測試基線 cbbd524 的 tree 與發布基線 32ec10231d70448ca43013036eec1f0869a21ce8 相同；本機已測程式548fce3的tree與發布程式6d97f7e8b969253bf4b3ef52df9db36959105c0a相同。regression摘要保留當時commit，不回填偽造。對應tree雜湊及驗證見validation-summary.json。

公開證據僅含控制流程、測試結果及內容雜湊；完整合成HTTP/學業payload不發布。請執行已提交的fixture runner重現細節。這是資料省略，不是以摘要冒充真實Gemini或跨user通過。
