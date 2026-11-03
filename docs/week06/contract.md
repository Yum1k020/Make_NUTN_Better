# 開工與驗收契約

| 欄位 | 契約 |
|---|---|
| 原子流程 | `planner_graduation.progress`／`graduation_workflow.progress_graph`，同一使用者的唯讀畢業進度 |
| 原缺口 | 前端固定示範資料；沒有具來源的模型說明與修正控制 |
| 原終點 | 回傳啟用規則下的畢業各項狀態，不取代校方認證 |
| 本次增量 | 原進度 → 結構化說明 A → 固定評估 → 至多修正 B → 同規準重評 |
| 輸入 | 後端目前使用者；不接受 client 傳 user_id／分數／規則／provider |
| state | context、previous draft、feedback、attempts、run_id、status、stop_reason、metrics |
| 下一步 | A 通過直接完成；A 未過才呼叫 B；B 未過停止；provider 錯誤即回退 |
| 規準 | 精確 rule_set_id／scope／overall／earned；每 check 出現一次；數字、null、狀態、source_ids、action 均符合來源 |
| 未知／缺件 | 未知仍 null；缺規則 model_calls=0；不借用舊結果 |
| 權限與確認 | 使用者按鈕觸發外部說明，畫面告知 Gemini 與資料範圍；無寫入工具，無自動改選課 |
| 上限 | A＋B 最多兩次；每次 I/O timeout 25 秒，回應 256 KiB，輸出 8192 tokens；無網路重試 |
| 拒絕／停止碼 | 入口 VALIDATION_ERROR／CROSS_ORIGIN_DENIED；RULE_UNAVAILABLE、PROVIDER_NOT_CONFIGURED、PROVIDER_*、REVISION_LIMIT、RUBRIC_PASS |
| 控制位置 | `graduation_explanation_api.py` 驗證與唯讀交易；core 評估及停止；gemini 接頭限制 I/O |
| 交接資訊 | 前端只顯示 verified clauses 或程式 fallback；原始 A/B 在處理紀錄與證據中可查，不顯示內部推理 |

## 四條 Given／When／Then

1. **正常。** Given 合成已通過 3 學分、修習中與規劃課程各一門、講座一類未知；When 真實 Gemini 說明；Then 已得仍 3、未知保留、來源齊全、正常回送並可顯示。**實際：LIVE_NOT_RUN，待設定。**
2. **非法輸入。** Given 請求夾帶 user_id、學分或未知 query；When POST 說明；Then 422、provider 0 次、資料庫不變。實際見離線測試。
3. **服務／工具失敗。** Given provider timeout／503，或規則 checksum 損壞；When 請求說明；Then provider 錯誤有限停止，資料庫錯誤在模型前停止，如實回報、不留寫入。注入與 live 分開。
4. **workflow 邊界。** Given A 故意錯學分、缺來源；When 評估；Then 拒絕並回送具體錯誤給 B；B 正確才接受；B 再錯就停止且不展示錯誤 claims。

其他斷言：null≠0、不接受未知 action／額外自由文字／重複 check／正式認證 scope；provider 無法透過改動收到的 context 影響權威資料。沒有記憶、上下文壓縮或持久化 workflow 的額外需求。
