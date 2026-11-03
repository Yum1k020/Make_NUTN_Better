# Week 06 架構決策總覽

## 決策一：智慧複習排程採 Prompt Chaining Gate

狀態：Accepted offline。真實 provider 狀態以當次 live evidence 為準。

只重構複習排程的 read-only preview：先驗證輸入，再由規則引擎排程，通過 deterministic Gate 後才允許模型說明。Gate 檢查必要欄位、日期、分鐘數、允許時段、busy interval、衝突與識別碼。拒絕時 business tool 與下游模型都必須是 0 次。

保留 `scheduler_v1`、`preview_study_plan`、Week 04/05 的人工確認及 `request_id` 冪等規則。未採 Routing、Parallelization 或動態 workers，因為這一段只有固定且相依的階段。代價是多一層 trace 與 Gate，正常 OpenAI runner 會有擷取與摘要兩次請求。

## 決策二：畢業缺項採受限 Evaluator–optimizer

狀態：Implemented candidate。真實 OpenAI 驗收仍需以最新環境重新執行。

保留一般程式的畢業計算與 checksum 驗證。OpenAI 只產生結構化說明 A；程式核對數字、`null` 狀態、來源、覆蓋範圍與可用 action。A 未通過時，將錯誤代碼回送模型產生 B，再用同一規準重評。最多兩稿，provider 失敗或 B 仍未達標時回退基本進度。

模型不取得逐筆修課、成績、姓名、學號、登入憑證或寫入工具。這項選擇提高可驗證性，但限制說明語氣，也增加 schema、評估器與測試維護成本。撤回程式即可回復，不需要資料遷移。

## 共同原則

- 一般程式保有正式數字、狀態、衝突與權限判斷。
- 模型只能使用已驗證的摘要或工具結果。
- 所有失敗都有有限出口，不自動無限重試。
- fixture 只證明控制行為，不能標示為 live provider 成功。
- trace 不保存金鑰、完整 prompt、私人行程、逐筆成績或模型內部推理。
