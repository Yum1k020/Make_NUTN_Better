# 前後比較與證據索引

## 固定案例與結果

固定使用者故事：「查看畢業進度，知道缺項、資料未知之處及下一步。」合成資料包含一門已通過 3 學分、一門修習中、一門規劃中、專業講座 10 場與一般講座未知。使用同一版 `nutn-csie-115-mvp-v1`、原畢業計算工具與原業務終點。

| 比較項目 | Before | After |
|---|---|---|
| 程式基線 | week05 `13be93782ef44e08886f86afffedd7f8fc72333d` | 本分支的程式提交；確切 SHA／source hashes 在 JSON |
| 畢業計算 | 原 GET 進度，既有 LangGraph | 同一進度計算，再新增說明與評估 |
| 前端 | `demo.js` 的固定示範數值 | 原 GET API 的目前使用者資料與規則版本 |
| 已取得學分 | 3 | 3；規劃中／修習中不納入 |
| 一般講座未知 | null、待確認 | 保留 null，畫面顯示待確認 |
| 說明品質控制 | 無本次的說明 A/B 功能 | A→固定評估→最多一次 B→同規準重評 |
| 注入錯誤 | 沒有本次的說明評估入口 | 錯學分／缺來源會拒絕，B 正確才通過；B 仍錯即停止 |
| 模型／工具次數 | 0 次模型、1 次原進度計算 | 最多 2 次模型、1 次原進度計算；實際 fixture 呼叫單獨標示 |
| 真實用量／費用 | 模型不適用 | 未取得；LIVE_NOT_RUN，沒有省費／省 token 的結論 |
| 失敗呈現 | 原 API 錯誤 | 模型錯誤保留基本進度；資料庫錯誤不呼叫模型 |
| 副作用 | 唯讀 | 唯讀；資料庫摘要前後相同 |

`exact-comparison.json` 是**獨立原始基線 checkout** 與候選程式對**同一 SQLite 資料快照**的實測。僅排除 `evaluated_at`，其餘全部 progress 欄位逐值相等；不是只比較學分總數，也沒有換規則來製造改善。

`acceptance.json` 另保留同次驗收 GET／POST 的實際耗時、run ID 與原始回應。第一個 GET 可能含框架冷啟動，fixture 沒有網路等待；這些耗時**不構成速度改善證據**。模型的 latency 與 token 欄位只有 live 真正取得時才有意義。

## 逐段證據

| 階段 | 檔案／欄位 |
|---|---|
| 請求與固定輸入 | `acceptance.json.inputs`、`exact-comparison.json.same_inputs` |
| 原工具結果 | `baseline.response.data`、`candidate.response.data.progress` |
| 模型 actual call | live 成功時 `workflow.attempts[].metrics.actual_call`，含 method、endpoint、request hash；目前 live 未執行，不能拿 fixture 填入 |
| 工具回送至模型 | 接頭將去識別的 progress 彙整放入 `contents` 的 evidence；不是聲稱 Gemini 發起 function call |
| 草稿 A／B | `workflow.attempts[].draft`、`label` |
| 檢查／回饋 | 同一 `rubric` 下的 `errors`、`passed`；修正收到 previous draft 與具體錯誤 |
| 結果／停止 | `status`、`stop_reason`、`model_calls`、`latency_ms` |
| 顯示／摘要 | `workflow.explanation`、`scope_text`、`ui-fixture.svg` |
| 來源追溯 | `evidence.rule_set_id`、check IDs、`source_ids`、`evidence_sha256` |
| 資料庫不變 | `acceptance.json.database_unchanged`、HTTP 測試前後完整 dump 比對 |
| 版本 | candidate source commit、source hashes；最終文件提交僅包裝已測程式與證據 |

來源 ID 表示「此版本規則下的某個計算 check」，不是外部校方文件頁碼。原計算仍驗證規則 checksum，未改成模型裁定資格。

## 預期與實際分開

1. **真實正常流程**：預期 Gemini 可回傳正確說明與用量；實際 `live.json` 為 **LIVE_NOT_RUN**。補驗證：設定伺服器端金鑰與可用模型，執行 `backend/week06_acceptance.py --live`，核對 live_status 及來源後再提交新的證據。
2. **非法輸入**：預期拒絕與零次 provider；實際 fixture HTTP 與測試通過，沒有寫入。
3. **服務／工具失敗**：預期有限停止與真實錯誤；實際 timeout、503、checksum 損壞皆為明示注入測試，通過；不宣稱遇到真實 Gemini 事故。
4. **workflow 邊界**：預期 A 錯誤會拒絕，B 同規準；實際注入 A 錯學分及缺來源，B 修正後通過；另測 B 仍錯為 REVISION_LIMIT。畫面圖為 fixture，並非 live。

## 回歸與分支整合

詳見 `regression-summary.json`、`merge-checks.json`。兩種畢業引擎均完成可執行回歸；4 條既有正式登入／未來 AI 測試維持 skipped。3 條未修改的 subprocess pipe 測試在 Windows 初次全跑失敗，後續明確排除，未假稱通過。新功能也經瀏覽器真正 HTTP 驗證。

7 個既有分支的確切 SHA 均經 pairwise merge-tree 檢查；另外在暫存 checkout 實際合併 `codex/frontend-week03-gate`，前端 15 項測試與建置通過，Vite config 同時保有原 agent middleware 與本次 `/api/v1` proxy。只保證記錄的分支版本；不等於保證後續未知變更永遠無衝突。

本次沒有實作正式登入、規則 v2 遷移或真正開課查詢。既有套件安裝仍有 audit 提示，未改鎖檔或聲稱完成相依安全整頓；這些是原專案另行維護範圍。
