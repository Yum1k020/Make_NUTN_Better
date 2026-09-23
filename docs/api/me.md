# 使用者資料 API：GET /me、PATCH /me

> 實作範圍：固定測試使用者 `user-demo-001`、本機 SQLite、`GET /api/v1/me` 與 `PATCH /api/v1/me`。分支為 `feature/user-profile-api`。以下保留使用者提供的契約，實測與未執行項目分開記錄。
> 本次結果：42 passed、2 skipped；正式登入及兩位登入使用者隔離均為「預期結果／未執行」，不列為通過。

### 1. 定義輸入與輸出

此 API 管理目前使用者的系所、入學年度、適用畢業規則與目前學期。

共同約定：

- API 前綴為 `/api/v1`。
- 使用者身分由後端取得，不接受前端指定 `user_id`。
- `rule_set_id` 由後端依系所與入學年度查找，不允許使用者直接修改。
- 入學年度使用民國年度，例如 `115`。
- 以下範例 ID 均為測試值，不代表校方正式代碼。

#### GET /me

**用途：** 取得目前使用者資料。

**輸入：**

| 項目 | 必填 | 說明 |
|---|---|---|
| 登入憑證 | 正式版必填 | baseline 使用後端固定測試身分 |
| 路徑參數 | 無 | 不需傳入使用者 ID |
| 查詢參數 | 無 | 不需額外條件 |
| Request body | 無 | 不傳送內容 |

**成功回應：`200 OK`**

```json
{
  "data": {
    "user_id": "user-demo-001",
    "department_id": "dept-csie",
    "admission_year": 115,
    "rule_set_id": "rules-csie-115-v1",
    "current_semester_id": "semester-115-1",
    "profile_complete": true,
    "rule_status": "matched"
  }
}
```

**回傳欄位合格條件：**

| 欄位 | 型別 | 合格條件 |
|---|---|---|
| `user_id` | string | 必須是目前使用者的識別碼 |
| `department_id` | string 或 null | 已設定時必須對應有效系所 |
| `admission_year` | integer 或 null | 已設定時為支援的民國入學年度 |
| `rule_set_id` | string 或 null | 必須符合該系所、入學年度的規則映射 |
| `current_semester_id` | string 或 null | 已設定時必須對應有效學期 |
| `profile_complete` | boolean | 系所、入學年度、目前學期皆已設定時為 true |
| `rule_status` | string | `matched`、`not_found`、`profile_incomplete` 之一 |

上述欄位均須出現。未設定的資料回傳 `null`，不可捏造預設值。

`profile_complete` 與 `rule_status` 分別表示資料填寫狀態與規則查找狀態；資料完整不代表一定找得到畢業規則。

#### PATCH /me

**用途：** 部分更新目前使用者資料；未傳入的欄位保持原值。

**輸入：**

| 欄位 | 型別 | 必填 | 驗證規則 |
|---|---|---|---|
| `department_id` | string | 條件必填 | 必須存在於系所資料 |
| `admission_year` | integer | 條件必填 | 必須存在於系統支援的入學年度清單 |
| `current_semester_id` | string | 條件必填 | 必須存在於學期資料 |

請求須使用 `Content-Type: application/json`，且至少提供上述一個欄位。所有可修改欄位均不接受 `null`；空物件、未知欄位、`user_id`、`rule_set_id` 均回傳 `422`。

**輸入範例：**

```json
{
  "department_id": "dept-csie",
  "admission_year": 115,
  "current_semester_id": "semester-115-1"
}
```

**成功回應：`200 OK`**

回傳與 `GET /me` 相同結構的完整最新資料，不能只回傳「修改成功」。

處理規則：

1. 將輸入與現有資料合併，再驗證。
2. 系所或入學年度變動時，重新查找適用規則。
3. 找不到規則仍可保存，回傳 `rule_set_id: null`、`rule_status: "not_found"`。
4. 任一輸入欄位無效時，整筆不保存。
5. 修改基本資料不得刪除既有修課、待辦或行程。

**錯誤回應格式：**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "輸入資料不合法",
    "fields": [
      {
        "field": "admission_year",
        "reason": "必須為系統支援的民國年度整數"
      }
    ]
  }
}
```

### 2. 驗收案例

**流程層次：**

- L1：識別使用者。baseline 為固定身分，正式版為登入驗證。
- L2：驗證 JSON、欄位、型別與可修改範圍。
- L3：檢查系所／學期等資料是否存在，查找適用規則。
- L4：讀取或以交易方式保存資料。
- L5：組成並驗證回應格式。

| 編號 | API／情境 | 測試輸入或前提 | 預期結果 | 流程停止位置 | 證據狀態 |
|---|---|---|---|---|---|
| G01 | GET 正常查詢 | 固定測試使用者已有完整資料 | `200`，回傳全部必要欄位及正確值 | 完成 L5 | 實測通過，見第 5 節及 JSON 證據 |
| G02 | GET 資料未填完 | 使用者系所與年度尚未設定 | `200`，缺值為 null，`profile_complete=false`、`rule_status=profile_incomplete` | 完成 L5 | 實測通過，見第 5 節及 JSON 證據 |
| G03 | GET 未登入，正式版 | 無有效登入憑證 | `401`，不回傳個人資料 | L1，不讀取個人資料 | 預期結果／未執行 |
| P01 | PATCH 正常修改 | 傳入有效系所、115 年度與有效學期 | `200`，回傳完整最新資料及正確規則；再次 GET 結果一致 | 完成 L5 | 實測通過，見第 5 節及 JSON 證據 |
| P02 | PATCH 部分修改 | 只傳有效的 `current_semester_id` | `200`，僅學期改變，其他欄位不變 | 完成 L5 | 實測通過，見第 5 節及 JSON 證據 |
| P03 | PATCH 型別錯誤 | `{"admission_year":"abc"}` | `422`，指出年度格式錯誤，資料不變 | L2，不進入保存 | 實測通過，見第 5 節及 JSON 證據 |
| P04 | PATCH 系所不存在 | `{"department_id":"unknown"}` | `422`，指出系所不存在，資料不變 | L3，不進入保存 | 實測通過，見第 5 節及 JSON 證據 |
| P05 | PATCH 學期不存在 | `{"current_semester_id":"unknown"}` | `422`，指出學期不存在，資料不變 | L3，不進入保存 | 實測通過，見第 5 節及 JSON 證據 |
| P06 | PATCH 無修改欄位或清空欄位 | 分別測試 `{}`、`{"department_id":null}` | 各回傳 `422`，資料不變 | L2，不進入保存 | 實測通過，見第 5 節及 JSON 證據 |
| P07 | PATCH 修改唯讀欄位 | 傳入 `user_id` 或 `rule_set_id` | `422`，拒絕修改，不影響任何使用者資料 | L2，不進入保存 | 實測通過，見第 5 節及 JSON 證據 |
| P08 | PATCH 部分欄位無效 | 有效學期搭配不存在的系所 | `422`，全部不保存，學期也保持原值 | L3，不進入保存 | 實測通過，見第 5 節及 JSON 證據 |
| P09 | PATCH 無對應規則 | 系所與年度有效，但規則映射不存在 | `200`，保存基本資料；規則為 null、狀態為 not_found | 完成 L5 | 實測通過，見第 5 節及 JSON 證據 |
| P10 | PATCH 儲存失敗 | 測試中模擬資料庫寫入失敗 | `500`，交易回滾，不回傳成功 | L4 | 實測通過，見第 5 節及 JSON 證據 |
| P11 | PATCH JSON 損壞 | 傳入未閉合的 JSON | `400`，提示請求格式錯誤 | L2，JSON 解析階段 | 實測通過，見第 5 節及 JSON 證據 |

**502 是否適用？**

這兩支 API 不呼叫 AI 或外部生成服務，因此 baseline **不使用「生成結果驗證失敗 502」案例**。

- 使用者輸入不合法：`422`。
- 本服務產生不符合契約的回應：`500`。
- 未來若接外部服務，收到無法使用的上游回應，再依契約設計 `502` 案例。

### 3. baseline

**最初可測試版本：固定測試使用者＋本機 SQLite＋預設參照資料。**

| 項目 | baseline 做法 |
|---|---|
| 使用者識別 | 後端固定為 `user-demo-001`，不接受前端指定 ID |
| 資料保存 | SQLite，驗證修改後及服務重啟後仍保留 |
| 系所、年度、學期 | 使用明確的測試資料清單 |
| 規則查找 | 用「系所＋入學年度」映射至唯一規則版本 |
| 更新方式 | PATCH 部分更新，所有寫入放在同一交易內 |
| 規則缺漏 | 允許保存基本資料，規則回傳 null 與 not_found |
| AI／校務服務 | 此版本不接入 |
| 正式登入 | 後續加入，再執行 401 與多使用者隔離測試 |

**選擇理由：**

此版本可先驗證欄位契約、規則映射、部分修改、錯誤處理與持久保存，測試結果不受登入供應商或校務系統影響。固定身分僅供本機開發與展示，不具備正式的多使用者隔離能力。

**已知無法通過的案例：兩位使用者資料隔離。**

- 前提：兩位不同使用者連線到 baseline。
- 操作：分別呼叫 `GET /me`。
- 正式版應有結果：各自取得自己的資料。
- baseline 預期表現：兩人都會取得固定測試使用者資料。
- 原因：尚未實作登入及身分映射。
- 證據狀態：**設計上已知限制／未執行，並非實測失敗。**


#### 實作細節與明確的 baseline 決策

- 使用 Python 內建 `sqlite3`，不需額外資料庫套件。預設檔案為 `backend/instance/profile.sqlite3`，每個請求使用獨立連線，啟用外鍵，結束後關閉。
- 初始化建立缺值全為 `null` 的測試使用者；重複初始化只補缺少資料，不重設已保存資料。G01／P01 測試自行建立完整資料，不把它當作新使用者的預設值。
- 系所清單：`dept-csie`、`dept-demo`；支援入學年度：`114`、`115`；學期：`semester-115-1`、`semester-115-2`。
- 唯一預設映射為 `(dept-csie, 115) → rules-csie-115-v1`。`dept-demo` 或 `114` 用於驗證無規則情境。這些都是測試資料，沒有匯入根目錄的正式畢業規則 JSON，也不執行畢業審核。
- 型別不做寬鬆轉換：`"115"`、`115.0`、`true` 均不是合法入學年度；所有可修改欄位的 `null` 都拒絕。JSON 頂層必須為非空物件。
- `rule_status` 優先看資料完整度：任一可修改欄位尚未設定時是 `profile_incomplete`。即使系所與年度已有匹配規則，只要學期未填，仍為此狀態；`rule_set_id` 可同時有有效映射值。資料完整後才區分 `matched`／`not_found`。
- PATCH 在 `BEGIN IMMEDIATE` 後讀取原值、合併與驗證，序列化同時寫入的請求以避免遺失部分更新；L3 驗證不通過時沒有 `UPDATE`。所有欄位以同一個 `UPDATE` 保存，不刪除或重建使用者。回應先通過 L5 驗證才 `COMMIT`；寫入或回應驗證失敗均 `ROLLBACK`。
- GET 以讀取交易取得一致快照，檢查參照資料、規則映射與輸出欄位。資料庫未初始化、資料庫錯誤或回應契約錯誤均回傳 `500`。
- 契約補充：PATCH Content-Type 不是 `application/json` 時回傳 `415`；JSON 損壞為 `400`；結構、欄位、型別、參照資料錯誤為 `422`。`application/json; charset=utf-8` 可接受。沿用環境的 1 MiB 請求上限，超限由框架回傳 `413`，本次未測試此環境上限。
- `400` 的 code 為 `INVALID_JSON`、`415` 為 `UNSUPPORTED_MEDIA_TYPE`、`422` 為 `VALIDATION_ERROR`、`500` 為 `INTERNAL_ERROR`；皆有 `error.code`、`error.message`、`error.fields`，非欄位錯誤的 `fields` 為空陣列。內部錯誤細節只寫服務端 log。

### 4. 執行方式

以下指令從儲存庫根目錄執行，需要 Python 3.12+。此 API 沿用專案既有 lock 檔，沒有新增第三方依賴。

```sh
# 安裝（本次沿用已存在的 .venv；沒有重新執行安裝）
./scripts/setup-backend.sh
# 如預設 Python 太舊，改用：
# PYTHON_BIN=/absolute/path/to/python3.12 ./scripts/setup-backend.sh

# 建表與補齊測試參照資料，不覆寫現有個人資料
./scripts/init-backend-db.sh

# 僅監聽本機；預設 port 5050
./scripts/run-backend.sh
# PORT=8000 ./scripts/run-backend.sh
```

若需指定資料庫，初始化和啟動皆使用同一絕對路徑：

```sh
ME_DATABASE=/absolute/path/demo.sqlite3 ./scripts/init-backend-db.sh
ME_DATABASE=/absolute/path/demo.sqlite3 ./scripts/run-backend.sh
```

Swagger UI：<http://127.0.0.1:5050/docs>；OpenAPI：<http://127.0.0.1:5050/openapi.json>。可在 Swagger 的 profile 區塊操作 GET／PATCH。

```sh
# 自動化驗收：使用獨立暫存 SQLite，不改動開發資料
./scripts/test-backend.sh

# 保存版本、逐筆輸入／實際輸出、資料前後比對、SQL trace、pytest 結果
# 請保留等號，避免 pytest 在載入自訂選項前將既有輸出檔當成測試路徑
./scripts/test-backend.sh --evidence=../docs/api/evidence/me-results.json
```

證據路徑相對於腳本切換後的 `backend/`。相同檔名會覆寫，若要保存歷次測試請換檔名。JSON 為每次執行自動生成；本 Markdown 是指定版本的驗收快照，後續改碼或重跑不會自動把新結果算作本次通過。

HTTP 重啟測試需要允許監聽 `127.0.0.1`。它用隨機可用 port 啟動真實服務程序、發送 HTTP 請求、停止程序，再以同一 SQLite 檔案啟動新程序，結束時停止服務；不留下背景程序。

以下是手動重現範例，未逐條以 curl 執行，不能將範例本身標為實測通過；對應行為已有第 5 節的自動化實測：

```sh
curl -i http://127.0.0.1:5050/api/v1/me
curl -i -X PATCH http://127.0.0.1:5050/api/v1/me \
  -H 'Content-Type: application/json' \
  -d '{"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}'
curl -i -X PATCH http://127.0.0.1:5050/api/v1/me \
  -H 'Content-Type: application/json' \
  -d '{"current_semester_id":"semester-115-2"}'
curl -i -X PATCH http://127.0.0.1:5050/api/v1/me \
  -H 'Content-Type: application/json' \
  -d '{"admission_year":"abc"}'
```

### 5. 真正執行的測試證據

- 測試日期：`2026-09-23T11:45:27.514715+08:00` 至 `2026-09-23T11:45:28.134461+08:00`（Asia/Taipei）。
- 分支：`feature/user-profile-api`；基底 commit：`1701d995b45b431445ef678b2fb69383c4721316`。
- 對應版本：**測試執行當時的未提交工作樹**，不能宣稱以上 HEAD 已包含實作。測試來源指紋（SHA-256）：`e6907dfa5522103528852270ff7a5e5cc5950a6c643ec8b251127f3e5a087366`。
- [完整機器可讀證據](evidence/me-results.json) 的 `source_sha256` 保存所有 API、測試、腳本、dev lock 與 pytest 設定的逐檔雜湊；可精確辨識本次測試的檔案內容。Markdown／README 本身不在程式指紋內。
- 環境：Python 3.12.14、SQLite 3.53.1；套件版本：`{"Flask": "3.1.3", "flask-smorest": "0.47.0", "marshmallow": "4.3.1", "pytest": "9.1.1"}`。
- 執行：`./scripts/test-backend.sh --evidence=../docs/api/evidence/me-results.json`；退出碼 `0`。

實際終端輸出：

```text
....s....................................s..                             [100%]
42 passed, 2 skipped in 0.60s
```

另外已實際執行 `./scripts/init-backend-db.sh`，輸出 `Initialized SQLite baseline (existing profiles preserved).`；`.venv/bin/python -m pip --isolated check` 輸出 `No broken requirements found.`。全新環境重新安裝尚未執行。

第一輪為 **39 passed、1 failed、2 skipped**，原始紀錄保留於 [第一次執行證據](evidence/me-initial-results.json)：X09 未成功啟動服務，沒有取得 HTTP 回應，不能算通過。另以 socket bind 確認沙箱回報 `PermissionError: [Errno 1] Operation not permitted`；允許本機監聽後成功完成 X09。整理時也發現使用空格傳入既有 `--evidence` 路徑會使 pytest 在收集前回報 `unrecognized arguments: --evidence`（退出碼 4，並未執行案例）；最終重現命令改用等號，且腳本明確指定 pytest 設定檔。下表僅採最後成功執行、與上述指紋相符的結果。

#### 前置資料與停止位置的證據

每項案例使用全新暫存資料庫及參照種子。需要完整資料的案例先 PATCH `dept-csie`／`115`／`semester-115-1`；所有準備呼叫也收錄於 JSON 的 `records`，不與正式請求混淆。

- L2：先驗證 request，失敗時不執行個人資料 SQL；L3：已讀取原值並驗證參照資料，但沒有 UPDATE。JSON 的 `sql_trace` 可檢查是否進入寫入。
- 所有錯誤請求均比對完整 `user_profiles` 的 before／after；P08 額外再次 GET，確認有效學期沒有部分保存。
- P10 以 SQLite `AFTER UPDATE` trigger 執行 `RAISE(FAIL)`，實際更新已開始後才故障；證據中可見 `ROLLBACK`，再次 GET 與原資料相同。
- X07 於 UPDATE 之後、COMMIT 之前注入回應驗證例外，證據同樣包含 `ROLLBACK` 與資料不變；這不是外部服務錯誤，也不回傳 502。
- X05 建立三張**測試用**修課／待辦／行程關聯表（含 ON DELETE CASCADE）以及另一筆使用者資料，驗證 PATCH 不刪除它們。正式修課、待辦、行程模組尚未存在，此測試不代表已完成那些模組的整合或登入隔離。
- 以下表格列出各案例的主要實測呼叫；完整準備、後續 GET、前後資料、SQL 與所有回應都保存在 JSON，依 `tests[].id` 對照。測試通過代表其所有 assert 完成，非僅檢查 HTTP 狀態碼。

#### 逐案例實際輸入與輸出

| 測試 ID（pytest 函式／參數） | 主要實際輸入 | 實際狀態碼 | 實際回應 | 結果 |
|---|---|---|---|---|
| `test_health_and_documentation_are_available_locally` | 環境介面與本機文件資源的 assertions | 見測試 assertions | 未額外錄製逐筆 body；pytest 實際通過 | 通過 |
| `test_json_validation_and_unicode_roundtrip` | 環境介面與本機文件資源的 assertions | 見測試 assertions | 未額外錄製逐筆 body；pytest 實際通過 | 通過 |
| `test_G01_complete_profile` | `GET（無 body）` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_G02_missing_values` | `GET（無 body）` | `200` | `{"data":{"admission_year":null,"current_semester_id":null,"department_id":null,"profile_complete":false,"rule_set_id":null,"rule_status":"profile_incomplete","user_id":"user-demo-001"}}` | 通過 |
| `test_G03_unauthenticated` | 尚未建立正式登入前提 | — | 預期結果／未執行 | 未執行（skip） |
| `test_P01_full_patch_and_get` | `PATCH {"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_P02_partial_patch` | `PATCH {"current_semester_id":"semester-115-2"}` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-2","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_P03_strict_integer[abc]` | `PATCH {"admission_year":"abc"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P03_strict_integer[115]` | `PATCH {"admission_year":"115"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P03_strict_integer[115.0]` | `PATCH {"admission_year":115.0}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P03_strict_integer[True]` | `PATCH {"admission_year":true}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P03_strict_integer[value4]` | `PATCH {"admission_year":[]}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P03_strict_integer[value5]` | `PATCH {"admission_year":{}}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P04_unknown_department` | `PATCH {"department_id":"unknown"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"department_id","reason":"系所不存在"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P05_unknown_semester` | `PATCH {"current_semester_id":"unknown"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"current_semester_id","reason":"學期不存在"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P06_empty_or_null[payload0]` | `PATCH {}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"body","reason":"必須為至少包含一個可修改欄位的 JSON 物件"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P06_empty_or_null[payload1]` | `PATCH {"department_id":null}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"department_id","reason":"必須為非 null 的字串"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P06_empty_or_null[payload2]` | `PATCH {"admission_year":null}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"必須為系統支援的民國年度整數"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P06_empty_or_null[payload3]` | `PATCH {"current_semester_id":null}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"current_semester_id","reason":"必須為非 null 的字串"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P07_readonly_or_unknown_field[user_id]` | `PATCH {"user_id":"other","current_semester_id":"semester-115-2"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"user_id","reason":"不允許修改此欄位"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P07_readonly_or_unknown_field[rule_set_id]` | `PATCH {"rule_set_id":"other","current_semester_id":"semester-115-2"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"rule_set_id","reason":"不允許修改此欄位"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P07_readonly_or_unknown_field[unexpected]` | `PATCH {"unexpected":"other","current_semester_id":"semester-115-2"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"unexpected","reason":"不允許修改此欄位"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P08_atomic_validation` | `PATCH {"department_id":"unknown","current_semester_id":"semester-115-2"}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"department_id","reason":"系所不存在"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_P09_missing_rule_and_rematch[change0]` | `PATCH {"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_P09_missing_rule_and_rematch[change1]` | `PATCH {"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_P10_database_failure_rolls_back` | `PATCH {"current_semester_id":"semester-115-2"}` | `500` | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取或保存使用者資料"}}` | 通過 |
| `test_P11_malformed_json` | `PATCH {"admission_year":115` | `400` | `{"error":{"code":"INVALID_JSON","fields":[],"message":"請求 JSON 格式錯誤"}}` | 通過 |
| `test_X01_unsupported_reference[payload0]` | `PATCH {"admission_year":116}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"admission_year","reason":"入學年度不受支援"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X01_unsupported_reference[payload1]` | `PATCH {"department_id":""}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"department_id","reason":"系所不存在"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X01_unsupported_reference[payload2]` | `PATCH {"current_semester_id":""}` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"current_semester_id","reason":"學期不存在"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X02_nonobject_json[null]` | `PATCH null` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"body","reason":"必須為至少包含一個可修改欄位的 JSON 物件"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X02_nonobject_json[[]]` | `PATCH []` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"body","reason":"必須為至少包含一個可修改欄位的 JSON 物件"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X02_nonobject_json["text"]` | `PATCH "text"` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"body","reason":"必須為至少包含一個可修改欄位的 JSON 物件"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X02_nonobject_json[115]` | `PATCH 115` | `422` | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"body","reason":"必須為至少包含一個可修改欄位的 JSON 物件"}],"message":"輸入資料不合法"}}` | 通過 |
| `test_X03_media_type` | `PATCH {}` | `415` | `{"error":{"code":"UNSUPPORTED_MEDIA_TYPE","fields":[],"message":"請使用 application/json"}}` | 通過 |
| `test_X04_incomplete_with_matching_rule` | `PATCH {"department_id":"dept-csie","admission_year":115}` | `200` | `{"data":{"admission_year":115,"current_semester_id":null,"department_id":"dept-csie","profile_complete":false,"rule_set_id":"rules-csie-115-v1","rule_status":"profile_incomplete","user_id":"user-demo-001"}}` | 通過 |
| `test_X05_related_records_and_other_profile_preserved` | `PATCH {"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_X06_init_idempotent` | `PATCH {"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_X07_invalid_response_rolls_back` | `PATCH {"current_semester_id":"semester-115-2"}` | `500` | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取或保存使用者資料"}}` | 通過 |
| `test_X08_openapi` | OpenAPI 的 GET／PATCH、requestBody 與狀態碼 assertions | 見測試 assertions | 未額外錄製逐筆 body；pytest 實際通過 | 通過 |
| `test_X09_real_http_process_restart` | `GET（無 body）` | `200` | `{"data":{"admission_year":115,"current_semester_id":"semester-115-2","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}` | 通過 |
| `test_X10_authenticated_user_isolation` | 尚未建立正式登入前提 | — | 預期結果／未執行 | 未執行（skip） |
| `test_X11_missing_database_returns_json_500` | `PATCH {"department_id":"dept-csie","admission_year":115,"current_semester_id":"semester-115-1"}` | `500` | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取或保存使用者資料"}}` | 通過 |
| `test_X12_inconsistent_stored_rule_returns_500` | `GET（無 body）` | `500` | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取或保存使用者資料"}}` | 通過 |

#### 額外驗收案例與停止層次

| ID | 情境／預期結果 | 停止層次 | 實測狀態 |
|---|---|---|---|
| X01 | 不支援年度、空白系所／學期 ID：422、資料不變 | L3 | 通過（3 組） |
| X02 | null、陣列、字串、數字作為頂層 JSON：422 | L2 | 通過（4 組） |
| X03 | text/plain：415 | L2 | 通過 |
| X04 | 有系所年度、尚無學期：200，規則已匹配但 profile_incomplete | 完成 L5 | 通過 |
| X05 | 合成關聯資料與另一筆使用者資料不被修改／刪除：200 | 完成 L5 | 通過，僅資料保存測試 |
| X06 | 重複 init-db 不覆寫已保存資料：GET 200 | 初始化後完成 L5 | 通過 |
| X07 | 服務端回應驗證失敗：500、回滾 | L5，commit 前 | 通過 |
| X08 | OpenAPI 列出兩支 API、輸入限制與回應狀態 | 文件產生 | 通過 |
| X09 | 真實 HTTP 修改、錯誤請求與服務程序重啟：重啟後 GET 200 且資料保留 | 完成 L5 | 通過 |
| X10 | 正式登入的多使用者隔離 | L1 身分映射尚缺 | 預期結果／未執行 |
| X11 | SQLite 路徑不存在／未初始化：GET 與 PATCH 均 JSON 500 | L4，連線失敗 | 通過 |
| X12 | 已存規則映射不一致：GET 500，不輸出違反契約的資料 | L5 | 通過 |

#### 真實 HTTP 與重啟紀錄（X09）

此段由本次實際紀錄整理。不是 Flask test client；PID 與 port 來自啟動的服務子程序。

```json
[
  {
    "phase": "before restart",
    "process_id": 58563,
    "port": 52078
  },
  {
    "transport": "real HTTP / subprocess",
    "method": "PATCH",
    "url": "http://127.0.0.1:52078/api/v1/me",
    "input": {
      "department_id": "dept-csie",
      "admission_year": 115,
      "current_semester_id": "semester-115-1"
    },
    "actual_status": 200,
    "actual_body": {
      "data": {
        "admission_year": 115,
        "current_semester_id": "semester-115-1",
        "department_id": "dept-csie",
        "profile_complete": true,
        "rule_set_id": "rules-csie-115-v1",
        "rule_status": "matched",
        "user_id": "user-demo-001"
      }
    }
  },
  {
    "transport": "real HTTP / subprocess",
    "method": "PATCH",
    "url": "http://127.0.0.1:52078/api/v1/me",
    "input": {
      "current_semester_id": "semester-115-2"
    },
    "actual_status": 200,
    "actual_body": {
      "data": {
        "admission_year": 115,
        "current_semester_id": "semester-115-2",
        "department_id": "dept-csie",
        "profile_complete": true,
        "rule_set_id": "rules-csie-115-v1",
        "rule_status": "matched",
        "user_id": "user-demo-001"
      }
    }
  },
  {
    "transport": "real HTTP / subprocess",
    "method": "PATCH",
    "url": "http://127.0.0.1:52078/api/v1/me",
    "input": {
      "admission_year": "abc"
    },
    "actual_status": 422,
    "actual_body": {
      "error": {
        "code": "VALIDATION_ERROR",
        "fields": [
          {
            "field": "admission_year",
            "reason": "必須為系統支援的民國年度整數"
          }
        ],
        "message": "輸入資料不合法"
      }
    }
  },
  {
    "transport": "real HTTP / subprocess",
    "method": "PATCH",
    "url": "http://127.0.0.1:52078/api/v1/me",
    "input": "{\"admission_year\":",
    "actual_status": 400,
    "actual_body": {
      "error": {
        "code": "INVALID_JSON",
        "fields": [],
        "message": "請求 JSON 格式錯誤"
      }
    }
  },
  {
    "transport": "real HTTP / subprocess",
    "method": "GET",
    "url": "http://127.0.0.1:52078/api/v1/me",
    "input": null,
    "actual_status": 200,
    "actual_body": {
      "data": {
        "admission_year": 115,
        "current_semester_id": "semester-115-2",
        "department_id": "dept-csie",
        "profile_complete": true,
        "rule_set_id": "rules-csie-115-v1",
        "rule_status": "matched",
        "user_id": "user-demo-001"
      }
    }
  },
  {
    "phase": "after restart",
    "process_id": 58564,
    "port": 52085
  },
  {
    "transport": "real HTTP / subprocess",
    "method": "GET",
    "url": "http://127.0.0.1:52085/api/v1/me",
    "input": null,
    "actual_status": 200,
    "actual_body": {
      "data": {
        "admission_year": 115,
        "current_semester_id": "semester-115-2",
        "department_id": "dept-csie",
        "profile_complete": true,
        "rule_set_id": "rules-csie-115-v1",
        "rule_status": "matched",
        "user_id": "user-demo-001"
      }
    }
  }
]
```

### 6. 未完成／未執行項目

| 項目 | 狀態與理由 |
|---|---|
| G03 未登入 401 | **預期結果／未執行**：尚未實作登入；baseline 固定使用者，不能據此聲稱認證通過。 |
| X10 兩位登入使用者隔離 | **設計上已知限制／未執行**：固定身分會共用資料；不是實測失敗，亦未標為通過。 |
| 正式修課、待辦、行程模組的整合 | **未執行**：目前只用合成關聯表驗證不刪資料。 |
| 前端串接、Swagger UI 手動點擊、逐條手動 curl | **未執行**：已有 OpenAPI 結構與自動 HTTP 測試，但不代替手動操作證據。 |
| 全新環境套件安裝 | **未執行**：沿用已建立的 .venv；已執行 pip check。 |
| 真實校方系所、入學年度、學期與規則版本導入 | **未執行**：本次僅測試種子與唯一映射。 |
| 外部 AI／校務服務、502 案例 | **不在本次範圍／未執行**：API 不呼叫外部服務。 |
| 高併發壓力、多程序競爭、正式部署、備份復原與 schema migration | **未執行**：使用 SQLite 交易不代表已完成這些驗收。 |
| 413 大型請求、其他未列舉的框架錯誤 | **未執行**：不將既有框架行為算成本次 API 驗收。 |

程式入口：[Flask app](../../backend/app/__init__.py)、[資料庫與初始化](../../backend/app/db.py)、[API 與驗證](../../backend/app/profile.py)、[驗收測試](../../backend/tests/test_me.py)、[證據收集](../../backend/tests/conftest.py)。後端環境隨此功能一併納入版本控制；原本另行準備的資料文件保留於本機，不納入本次 API 提交。測試紀錄保留執行當時的基底 commit 與來源雜湊，不因後續提交而改寫歷史證據。
