# 學生個人安排 API：實作與實測

本文件記錄已實作的 Flask baseline 與真正執行的測試。[原始規格](student-planner-spec.md) 保留使用者提供的完整輸入／輸出、必填欄位、型別與預期案例；原文的「未執行」不會因實作存在而自動變成通過。本文件與原始 JSON 證據才是本輪實測紀錄。

## 待辦功能更新

`feature/task-api-enhancements` 已將舊 FastAPI 待辦原型的描述、優先級、無期限待辦、分頁與資料庫健康檢查移植至 Flask。最新契約見 [待辦擴充說明](task-api-enhancements.md)；下方測試紀錄及原始規格保留為歷史版本。

## 實作範圍與 baseline

沿用專案已決定的 Flask，並非原附件提及的 FastAPI。SQLite、固定使用者 `user-demo-001`，全部業務端點使用 `/api/v1`。既有 `/me`、學期及課程查詢保持相容；既有前端尚未串接。

| 功能 | 實作 |
| --- | --- |
| 修課、課表、待辦、私人行程、複習計畫、規劃課程 | 六組 GET 清單／單筆、POST、PATCH、DELETE |
| 行事曆與首頁 | `/calendar`、`/dashboard`，共享資料來源、期限與占用分開 |
| 衝突與空閒 | `/schedule/conflicts`、`/schedule/availability`，半開區間、聯集扣除、未知課程警告 |
| 複習安排 | 計畫 `/generate` 預覽、GET／PUT `/sessions`，單一 `/study-sessions/{id}` PATCH／DELETE，版本檢查 |
| 選課檢查 | `/planned-courses/check`，先修、重複及衝突，預覽不寫入 |
| 畢業 | `/graduation-rules/{id}`、`/programs`、`/lecture-progress` GET／PUT、`/graduation-progress` |
| 地圖 | `/campus-maps` 與三張既有靜態圖片 |

個人資源存於 `planner_resources` JSON 欄位，使用 SQLite 唯一索引防止重複，歸屬過濾與關聯驗證由服務層處理；不是每種資源各建一張關聯表。寫入使用單一交易，課表自動建立修課、刪除行程清除待辦關聯、整組替換複習時段均可回滾。唯讀與預覽交易設 `query_only`。修課快照保存當下課名／學分與來源雜湊。

生成使用確定性最早可用時段演算法，不呼叫 AI；不足時回傳部分安排，不會自動保存。保存時重新檢查當下占用、時間窗及 `plan_version`。時間皆轉為 Asia/Taipei，行事曆最多 31 天、安排範圍最多 60 天。

## 輸入與輸出

完整欄位表與各端點回應見[原始規格](student-planner-spec.md)，可操作請求 schema 見啟動後 `/docs` 或 `/openapi.json`。OpenAPI 的成功回應以共用 envelope 描述，完整巢狀業務欄位以原規格及下方實測 JSON 為準。

- POST 必填欄位依資源驗證；PATCH 至少一個可修改欄位，未提供值保留，僅允許 nullable 欄位清空。
- 不接受 `user_id`、未知欄位、未知／重複 query；數值不接受布林冒充整數，日期時間必須帶時差。
- 成功單筆 `{"data": {...}}`、清單 `{"data": [], "meta": {"count": 0}}`；DELETE 204 無內容。
- JSON 解析失敗 400、欄位／參照錯誤 422、資源不存在或不屬於目前使用者 404、衝突／重複／關聯／版本錯誤 409、儲存或輸出損壞 500。錯誤 envelope 為 `error.code/message/fields`。

## 規則資料與已知限制

內建 `backend/app/data/nutn_csie_115_graduation_rules_v1.json` 是團隊第一版草案，133 學分、三學程擇二、專業講座 10／通識講座 12，非校方正式認證。規則内容雜湊固定，同版本内容被改動時初始化拒絕覆寫。

為保留原 `/me` 測試資料，新增 `dept-nutn-csie`／115 對應 `nutn-csie-115-mvp-v1`。原 `dept-csie` 的合成規則不會自動套用 133 學分。可 PATCH `/me`：

```json
{"department_id":"dept-nutn-csie","admission_year":115,"current_semester_id":"semester-115-1"}
```

正式課程 ID 對照、學分分類與通識領域尚未完成。`graduation_course_mappings`、`graduation_course_domains` 保留人工確認的對照；不按同名猜測、不把未知當 0。未映射必修與學程回傳待確認，缺規則的學分總數為 null。B20 的 133 學分全達標案例使用**測試專用合成對照**，不表示真實學生已達畢業門檻。

目前不支援正式登入、重修、例假日／停課例外、移動緩衝時間或外部 AI；SQLite JSON 資源適合此 baseline，正式多使用者部署、資料遷移及效能尚未驗證。

## 執行方式

在儲存庫根目錄執行：

```sh
./scripts/setup-backend.sh
./scripts/init-backend-db.sh
./scripts/run-backend.sh
# 另一個終端機
./scripts/test-backend.sh --evidence=../docs/api/evidence/planner-results.json
```

更新既有環境後仍需重新執行 init，建立新增表與規則種子；可重複執行且保留資料。預設資料庫 `backend/instance/profile.sqlite3`，可用 `ME_DATABASE=/absolute/path/db.sqlite3` 同時指定初始化與啟動資料庫。API：`http://127.0.0.1:5050/api/v1`；Swagger：`http://127.0.0.1:5050/docs`。測試使用暫存資料庫，真實 HTTP 重啟測試需要允許監聽 127.0.0.1。本輪沒有修改開發資料庫。

## 真正的測試證據

- 日期：2026-09-24T22:31:09.787219+08:00 至 2026-09-24T22:31:15.214922+08:00（Asia/Taipei）。
- 分支：`feature/student-planner-api-flask`；基礎 commit：`d32c99b6c88eda6590111e650698e6addc0c4a8c`。
- 受測版本是尚未提交的工作樹，不能以 HEAD 當作新實作版本。來源 fingerprint：`f8f56710dd5f52da6f23ec56f7fd336687c2bd832d7b138f1ebb25427ac6595d`，各檔 SHA-256 見原始報告。
- 環境：Python 3.12.14、SQLite 3.53.1；套件版本見報告。
- 實際執行：`./scripts/test-backend.sh -x --evidence=../docs/api/evidence/planner-results.json`，exit 0，**252 passed、4 skipped**。
- [完整原始證據](evidence/planner-results.json)：每個測試 ID、結果、輸入、實際 HTTP 狀態／JSON、SQL trace、前後資料快照與雜湊；成功與失敗停止層次來自應用程式 log。大部分使用 Flask test client；B19 另以真正 HTTP 程序建立資料並重啟後讀回。

停止層次：L1 HTTP 邊界、L2 JSON／格式、L3 歸屬／參照／資源規則、L4 時間與衍生計算、L5 寫入、L6 回應。成功請求記錄最終 L6；錯誤保留實際停止處。HTTP 實際程序測試不擷取內部層次，標示未記錄。

### 實際輸入／輸出範例

`POST /api/v1/enrollments`，預期／實際 422/422，通過。

輸入：
```json
{
  "course_id": "course-demo-001",
  "semester_id": "semester-115-1",
  "enrollment_status": "finished",
  "passed": true,
  "grade": 50
}
```

實際輸出：
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "fields": [
      {
        "field": "grade",
        "reason": "成績與通過狀態矛盾"
      }
    ],
    "message": "輸入資料不合法"
  }
}
```

`POST /api/v1/enrollments`，預期／實際 201/201，通過。

輸入：
```json
{
  "course_id": "course-demo-001",
  "semester_id": "semester-115-1",
  "enrollment_status": "finished",
  "passed": true,
  "grade": 80
}
```

實際輸出：
```json
{
  "data": {
    "course_id": "course-demo-001",
    "course_snapshot": {
      "course_id": "course-demo-001",
      "credits": 3.0,
      "name": "資料結構",
      "version_basis": "sha256:39fcc5770e98456071632ac1e4b8b4013ac387b31a2419177c5a88ada23e8209"
    },
    "created_at": "2026-09-24T22:31:13.575194+08:00",
    "enrollment_id": "84c9fe47-c74d-4e51-859e-819b092ddcd5",
    "enrollment_status": "finished",
    "grade": 80,
    "offering_id": null,
    "passed": true,
    "semester_id": "semester-115-1",
    "updated_at": "2026-09-24T22:31:13.575194+08:00",
    "user_id": "user-demo-001"
  }
}
```

### 驗收索引

下表直接由最後一輪報告整理；一個測試可能涵蓋數個案例與多次請求，因此狀態碼／層次為該測試觀察值集合。詳細逐次預期值、輸入與實際輸出請依測試名稱查原始報告。X06 僅通過固定身分的資料歸屬測試，正式登入隔離仍未執行。

| 案例／測試名稱 | 結果 | 預期狀態碼集合 | 實際狀態碼集合 | 實際停止層次 |
| --- | --- | --- | --- | --- |
| `X01_X02_X04_crud_roundtrip` | 通過 | 200, 201, 204, 404 | 200, 201, 204, 404 | L3, L6 |
| `X03_readonly_or_empty_patch` | 通過 | 201, 422 | 201, 422 | L2, L6 |
| `X05_missing_resource` | 通過 | 404 | 404 | L3 |
| `X06_baseline_owner_filter` | 通過 | 200, 201, 404 | 200, 201, 404 | L3, L6 |
| `X07_formal_authentication` | 未執行（skip） | — | — | 未記錄 |
| `X08_storage_failure` | 通過 | 200, 201, 500 | 200, 201, 500 | L5, L6 |
| `X09_X10_bad_json_and_user_id` | 通過 | 400, 422 | 400, 422 | L2 |
| `E01_E02_E03_enrollment` | 通過 | 200, 201, 409, 422 | 200, 201, 409, 422 | L3, L6 |
| `T01_E04_timetable_link` | 通過 | 200, 201, 204, 409 | 200, 201, 204, 409 | L3, L6 |
| `T02_bad_weekday` | 通過 | 200, 422 | 200, 422 | L2, L6 |
| `T03_conflicting_timetable` | 通過 | 200, 201, 409 | 200, 201, 409 | L4, L6 |
| `T04_link_write_rollback` | 通過 | 200, 500 | 200, 500 | L5, L6 |
| `CA01_calendar_dedup_and_deadlines` | 通過 | 200, 201 | 200, 201 | L6 |
| `CA02_invalid_calendar_range` | 通過 | 422 | 422 | L2 |
| `CA03_outside_semester` | 通過 | 200, 201 | 200, 201 | L6 |
| `TA01_TA02_TA03_task` | 通過 | 200, 201, 422 | 200, 201, 422 | L2, L6 |
| `PE01_PE02_cross_day` | 通過 | 200, 201, 422 | 200, 201, 422 | L3, L6 |
| `PE03_conflict_with_study` | 通過 | 200, 201, 409 | 200, 201, 409 | L4, L6 |
| `CF01_CF02_overlap_and_boundary` | 通過 | 200, 201 | 200, 201 | L6 |
| `CF03_GE03_unknown_class` | 通過 | 200, 201, 409 | 200, 201, 409 | L4, L6 |
| `AV01_AV02_AV03_availability` | 通過 | 200, 201 | 200, 201 | L6 |
| `SP01_SP02_SP03_plan_validation` | 通過 | 200, 201, 409, 422 | 200, 201, 409, 422 | L2, L3, L4, L6 |
| `GE01_GE02_generation` | 通過 | 200, 201 | 200, 201 | L6 |
| `GE04_future_ai` | 未執行（skip） | — | — | 未記錄 |
| `SS01_SS02_SS03_recheck_and_version` | 通過 | 200, 201, 409 | 200, 201, 409 | L3, L4, L6 |
| `SS04_SS05_session_adjustment` | 通過 | 200, 201, 204, 409 | 200, 201, 204, 409 | L4, L6 |
| `PC01_PC02_planning_does_not_earn_credits` | 通過 | 200, 201, 409 | 200, 201, 409 | L3, L6 |
| `CK01_CK02_planning_check` | 通過 | 200 | 200 | L6 |
| `GR01_GR02_PR01_PR02_rules` | 通過 | 200, 404, 422 | 200, 404, 422 | L2, L3, L6 |
| `LP01_LP02_LP03_lectures` | 通過 | 200, 422 | 200, 422 | L2, L6 |
| `GP01_GP02_GP03_GP04_progress` | 通過 | 200, 201 | 200, 201 | L6 |
| `GP05_allocation_once` | 通過 | 200, 201 | 200, 201 | L6 |
| `DB01_DB02_dashboard` | 通過 | 200, 201, 422 | 200, 201, 422 | L2, L6 |
| `MP01_MP02_maps` | 通過 | 200 | 200 | L6 |
| `B01_task_event_reference_cleanup` | 通過 | 200, 201, 204 | 200, 201, 204 | L6 |
| `B02_exam_links_guarded` | 通過 | 200, 201, 204, 409 | 200, 201, 204, 409 | L3, L6 |
| `B03_plan_sessions_isolation_tail_and_clear` | 通過 | 200, 201, 204, 404 | 200, 201, 204, 404 | L3, L6 |
| `B04_put_rollback_after_delete` | 通過 | 200, 201, 500 | 200, 201, 500 | L5, L6 |
| `B05_invalid_session_sets` | 通過 | 201, 422 | 201, 422 | L4, L6 |
| `B06_exclusion_ownership_and_self_edit` | 通過 | 200, 201, 404 | 200, 201, 404 | L3, L6 |
| `B07_enrollment_calendar_and_manual_override` | 通過 | 200, 201, 409 | 200, 201, 409 | L3, L6 |
| `B08_catalog_entry_and_mismatched_offering` | 通過 | 201, 422 | 201, 422 | L3, L6 |
| `B09_task_filter_order_null_and_partial_dates` | 通過 | 200, 201, 422 | 200, 201, 422 | L2, L3, L6 |
| `B10_timezone_and_read_only_preview` | 通過 | 200, 201, 422 | 200, 201, 422 | L2, L6 |
| `B11_missing_rule_dashboard_no_fake_numbers` | 通過 | 200 | 200 | L6 |
| `B12_snapshot_immutable_and_invalid_output` | 通過 | 200, 201, 500 | 200, 201, 500 | L3, L6 |
| `B13_unknown_query_all_crud` | 通過 | 422 | 422 | L2 |
| `B14_sql_read_error_is_500` | 通過 | 500 | 500 | L3 |
| `B15_openapi_paths` | 通過 | — | — | 未記錄 |
| `B16_week_boundary_study_minutes` | 通過 | 200, 201 | 200, 201 | L6 |
| `B17_lecture_storage_rollback` | 通過 | 200, 500 | 200, 500 | L5, L6 |
| `B18_init_preserves_data_and_rule_version` | 通過 | 200, 201 | 200, 201 | L6 |
| `B19_real_http_and_restart` | 通過 | — | 200, 201 | 未記錄 |
| `B20_fully_mapped_synthetic_graduation_met` | 通過 | 200 | 200 | L6 |
| `B21_successful_session_patch_and_version` | 通過 | 200, 201, 409 | 200, 201, 409 | L3, L6 |
| `B22_in_progress_is_not_passed_prerequisite` | 通過 | 200, 201 | 200, 201 | L6 |
| `B23_unknown_query_calculation_endpoints` | 通過 | 422 | 422 | L2 |

### 保留的失敗與回歸紀錄

| 報告 | 當輪結果與處理 |
| --- | --- |
| [planner-regression.json](evidence/planner-regression.json) | 原功能 124 通過、2 跳過 |
| [planner-first.json](evidence/planner-first.json) | 86 通過、1 失敗、2 跳過；E02 的測試先建立重複資料而先回 409，調整案例順序後重測 |
| [planner-second.json](evidence/planner-second.json) | 108 通過、1 失敗、2 跳過；B07 測試殘留不匹配 offering 而先回 422，調整輸入後重測 |
| [planner-openapi-failure.json](evidence/planner-openapi-failure.json) | 4 失敗、248 setup error、4 跳過；OpenAPI 註冊缺 Flask rule，修正後全套重跑 |
| [planner-results.json](evidence/planner-results.json) | 最後一輪 252 通過、4 跳過，非沿用之前結果 |

### 未完成／未執行

- 正式登入 401、雙登入使用者隔離：未執行（原 /me G03、X10；本規格正式 X06／X07），共三筆 skip 記錄。
- GE04 外部 AI 無效結果 502：未執行，一筆 skip；本版使用確定性本機生成。
- 真實校務課程對照、官方規則認證、真實學生畢業認定：未執行；合成資料通過不代表以上通過。
- 前端串接、正式部署、壓力與多程序併發負載：未執行。
