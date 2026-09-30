# 學生個人安排系統 API 規格

## 1. 共用約定

### 1.1 路徑與 CRUD

全部端點使用 `/api/v1` 前綴。本文表格省略此前綴。

標示 CRUD 的資源統一提供：

| 操作 | 方法與路徑 | 成功狀態 |
|---|---|---|
| 清單 | `GET /resources` | 200 |
| 詳細資料 | `GET /resources/{id}` | 200 |
| 新增 | `POST /resources` | 201 |
| 部分修改 | `PATCH /resources/{id}` | 200 |
| 刪除 | `DELETE /resources/{id}` | 204，無回應內容 |

POST 表格中的必填欄位，表示新增時必填。PATCH 至少提供一個允許修改的欄位，未提供者保留原值，合併後重新驗證。

### 1.2 資料格式與身分

- baseline 使用固定測試使用者；正式版由登入憑證識別使用者。
- 不接受前端指定或修改 `user_id`。
- 查詢與修改均限制在目前使用者的資料；他人的資源 ID 回傳 404。
- ID 使用字串，由後端產生。
- 日期：`YYYY-MM-DD`。
- 日期時間：含時差的 ISO 8601，例如 `2026-10-05T14:00:00+08:00`。
- 時區：`Asia/Taipei`。
- 星期：1～7，1 為星期一。
- 時長：整數分鐘。
- `null` 表示未知，不等於 0、未通過或沒有條件。
- 未定義欄位與不支援的查詢參數回傳 422。

新增時未提供的選填欄位，依文件設為 null 或明確預設值。PATCH 只有明確允許為 null 的欄位可以清空。

### 1.3 成功與錯誤格式

單筆資料：

```json
{
  "data": {
    "task_id": "task-demo-001",
    "title": "資料結構作業"
  }
}
```

清單：

```json
{
  "data": [],
  "meta": {
    "count": 0
  }
}
```

錯誤：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "輸入資料不合法",
    "fields": [
      {
        "field": "ends_at",
        "reason": "結束時間必須晚於開始時間"
      }
    ]
  }
}
```

| 狀態碼 | 使用情境 |
|---|---|
| 200 | 查詢、修改、預覽、計算成功 |
| 201 | 新增資源成功 |
| 204 | 刪除成功 |
| 400 | JSON 無法解析 |
| 401 | 正式版沒有有效登入憑證 |
| 404 | 路徑指定資源不存在，或不屬於目前使用者 |
| 409 | 時間衝突、重複資料、版本過期或關聯限制 |
| 422 | 欄位、格式、參照 ID 或業務輸入不合法 |
| 500 | 資料庫失敗、內部計算結果不符合契約 |
| 502 | 接入外部 AI 後，上游生成結果經驗證仍不合法 |

所有失敗的寫入操作都不得留下部分更新。非欄位錯誤的 `fields` 為空陣列；衝突錯誤可另外附上 `conflicts`。

### 1.4 流程層次

| 層次 | 工作 |
|---|---|
| L1 | 識別目前使用者與存取權限 |
| L2 | 解析請求，驗證必填、型別、格式 |
| L3 | 查詢參照資料、驗證歸屬及業務条件 |
| L4 | 執行排程、衝突、畢業規則等計算；需要時呼叫外部 AI |
| L5 | 驗證計算結果，重新檢查衝突並以交易保存 |
| L6 | 組成並驗證回應 |

只讀 API 不執行保存。查詢不存在的個人資源通常停在 L3。L3 可能已讀取資料庫，但不得開始未經驗證的寫入。

### 1.5 時間與衝突規則

- 佔用時段包含：課表、私人行程、已保存的複習時段。
- 待辦截止時間本身不佔用時間。
- 時段使用半開區間 `[開始, 結束)`：10:00 結束與 10:00 開始不算衝突。
- 編輯時排除自身，但不能排除其他使用者或其他計畫的任意資料。
- 相同時段重複出現在不同資料來源時，須以穩定來源 ID 避免重複呈現。
- baseline 不考慮跨校區交通緩衝、假日停課及單次調課。
- 已知有課程但時間不明時，不得回傳「已確認無衝突」；以警告與不完整狀態表示。

---

## 2. 定義輸入與輸出

### 2.1 個人修課紀錄 `/enrollments` CRUD

**用途：** 保存當期修習與歷年通過紀錄，作為課表和畢業審核的依據。

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `course_id` | 是 | 有效課程 ID |
| `semester_id` | 是 | 有效學期 ID |
| `offering_id` | 否 | 可為 null；有值時必須符合課程與學期 |
| `enrollment_status` | 是 | `in_progress` 或 `finished` |
| `passed` | 條件必填 | finished 時為 boolean；in_progress 時為 null |
| `grade` | 否 | null 或 0～100 的數字 |

清單支援 `semester_id`、`enrollment_status` 篩選。

#### 輸出合格條件

回傳上述欄位，以及：

- `enrollment_id`、`user_id`。
- `course_snapshot`：保存有效的課名、學分及課程版本依據。
- `created_at`、`updated_at`。

#### 業務規則

- `grade >= 60` 時 `passed` 必須為 true；低於 60 時必須為 false。
- `finished` 可沒有數字成績，但必須明確提供 `passed`。
- 修習中不接受非 null 的成績或通過狀態。
- 同一使用者、課程、學期不得重複建立。
- 第一版不支援同課跨學期的重修建檔，遇到已有該課紀錄時回傳 409，不重複採計。
- 只有 finished 且 passed=true 的紀錄計入已取得學分。
- 若紀錄已被手動課表引用，直接刪除回傳 409，須先移除課表關聯。

### 2.2 手動課表 `/timetable-entries` CRUD

**用途：** 以單一操作維護個人課表與相關修課關聯。

一筆 entry 代表一门課在某學期的一組每週時段，不是一個單次事件。

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `semester_id` | 是 | 有效學期 |
| `course_id` | 是 | baseline 必須選擇既有課程 |
| `offering_id` | 否 | 選擇共用開課；與手動 meetings 模式互斥 |
| `section_name` | 否 | 手動模式可填，否則取開課資料 |
| `meetings` | 條件必填 | 未選 offering_id 時至少一筆 |

每筆 `meetings` 包含：

- `weekday`：1～7。
- `start_time`、`end_time`：有效時間，結束晚於開始。
- `campus_id`、`location`：選填，可為 null。

清單支援 `semester_id` 篩選。

#### 輸出合格條件

回傳：

- `entry_id`、`user_id`。
- `semester_id`、`course_id`、`offering_id`、`enrollment_id`。
- `section_name`、完整 `meetings`。
- `source_type`：`catalog` 或 `manual`。
- `created_at`、`updated_at`。
- `warnings`：例如無法完整檢查的未知時段。

#### 業務規則

- 選共用開課時，時段取自開課資料，不允許透過此 API 修改共用班別。
- 手動模式的時段是個人覆寫資料，不影響其他學生。
- 後端在同一交易中建立或沿用修課紀錄及必要的個人開課關聯。
- 已存在相同課程與學期的 entry 時回傳 409。
- 新增或修改後，對學期有效期間執行衝突檢查；已知衝突回傳 409。
- 刪除 entry 只移除個人課表安排，不刪除歷年修課與通過紀錄。
- baseline 不提供在此端點建立全新課程目錄的功能。

### 2.3 日／週行事曆 `GET /calendar`

#### 輸入

| 參數 | 必填 | 規則 |
|---|---|---|
| `from` | 是 | 日期，包含當日 |
| `to` | 是 | 日期，包含當日；不得早於 from |

baseline 一次最多查詢 31 個日曆日。

#### 輸出合格條件

```json
{
  "data": {
    "from": "2026-10-05",
    "to": "2026-10-11",
    "timezone": "Asia/Taipei",
    "events": [],
    "task_deadlines": [],
    "warnings": []
  }
}
```

`events` 每筆包含：

- `event_key`：展開後的穩定唯一鍵。
- `source_type`：`class`、`personal_event`、`study_session`。
- `source_id`、`title`。
- `starts_at`、`ends_at`、`location`。

`task_deadlines` 每筆包含：

- `task_id`、`title`、`type`。
- `due_date`、`due_time`、`completed`。

#### 業務規則

- 課表只在對應學期起訖範圍內展開。
- 回傳與查詢日期範圍有交集的事件；保留事件原始起訖。
- events 依開始時間及 event_key 排序。
- 待辦另列，不自動產生佔用時段。
- 未知課表時間以 warnings 表示，不捏造事件。
- 若同一修課透過 enrollment 與 timetable-entry 都可取得，只展開一次；個人手動時段優先。

### 2.4 待辦事項 `/tasks` CRUD

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `title` | 是 | 去除前後空白後 1～200 字 |
| `type` | 是 | `todo`、`assignment`、`report`、`exam`、`review` |
| `course_id` | 否 | 有效課程或 null |
| `due_date` | 是 | 有效日期 |
| `due_time` | 否 | 有效時間或 null |
| `completed` | 否 | boolean，新增預設 false |
| `event_id` | 否 | 本人行程 ID 或 null |

清單支援 `from`、`to` 篩選截止日期，以及 `completed`、`course_id`。

#### 輸出合格條件

回傳全部輸入欄位，以及 `task_id`、`user_id`、`created_at`、`updated_at`。

#### 業務規則

- 只有日期的待辦不自動補上午夜截止時間。
- 考試若要佔用時間，須另建私人行程並關聯。
- 同一天依 due_time 排序，沒有時間者置後，再依 task_id 排序。
- 刪除被複習計畫引用的考試待辦回傳 409，須先解除引用。
- 刪除待辦不連帶刪除私人行程。

### 2.5 私人行程 `/personal-events` CRUD

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `title` | 是 | 1～200 字 |
| `starts_at` | 是 | 含時差的日期時間 |
| `ends_at` | 是 | 晚於 starts_at |
| `location` | 否 | 字串或 null |

清單可使用 `from`、`to` 日期時間，查詢有交集的行程。

#### 輸出合格條件

回傳輸入欄位，以及 `event_id`、`user_id`、`created_at`、`updated_at`。

#### 業務規則

- 支援跨日行程。
- baseline 不提供週期性重複行程。
- 新增或修改時，與課表、私人行程、已保存複習時段衝突則回傳 409。
- 修改時排除自己的 event_id。
- 刪除行程時，在同一交易中將待辦對它的 event_id 引用清為 null。

### 2.6 衝突預覽 `POST /schedule/conflicts`

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `starts_at` | 是 | 候選事件開始時間 |
| `ends_at` | 是 | 候選事件結束時間 |
| `exclude_source` | 否 | 編輯時排除自身來源，須驗證本人歸屬 |

`exclude_source` 包含 `source_type`、`source_id`。

#### 輸出合格條件

```json
{
  "data": {
    "has_conflict": true,
    "check_complete": true,
    "conflicts": [
      {
        "source_type": "class",
        "source_id": "meeting-demo-001",
        "title": "資料結構",
        "overlap_starts_at": "2026-10-05T09:30:00+08:00",
        "overlap_ends_at": "2026-10-05T10:00:00+08:00"
      }
    ],
    "warnings": []
  }
}
```

#### 業務規則

- 有衝突仍回傳 200，因為預覽成功完成。
- `has_conflict` 表示是否找到已知衝突。
- 若資料有未知時段，`check_complete=false`；即使 has_conflict=false，也不能宣稱完全無衝突。
- 本端點不保存任何事件。

### 2.7 空閒時段 `POST /schedule/availability`

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `from` | 是 | 含時差日期時間 |
| `to` | 是 | 晚於 from；最大查詢範圍 60 天 |
| `allowed_windows` | 是 | 至少一筆候選可用區間 |
| `min_duration_minutes` | 否 | 正整數，預設 1 |

每筆 allowed_windows 包含 `starts_at`、`ends_at`，必須在查詢範圍內。

#### 輸出合格條件

回傳：

- `free_slots`：每筆含 starts_at、ends_at、duration_minutes。
- `total_free_minutes`：符合最短時長的 free_slots 加總。
- `check_complete`、`warnings`。

#### 業務規則

- 先合併重疊的可用區間，避免重複計算分鐘。
- 扣除課表、私人行程、已保存複習時段的聯集。
- 不扣除只有截止日期的待辦。
- 沒有空閒時段回傳 200、空陣列及 0 分鐘。
- 有未知佔用時間時回傳 check_complete=false。

### 2.8 複習需求 `/study-plans` CRUD

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `course_id` | 是 | 有效課程 |
| `exam_task_id` | 否 | 本人 exam 類型待辦或 null |
| `start_date` | 是 | 開始安排日期 |
| `exam_date` | 是 | 晚於 start_date，規劃範圍最多 60 天 |
| `target_minutes` | 是 | 正整數 |
| `session_minutes` | 是 | 正整數 |
| `allowed_windows` | 是 | 至少一筆每週可安排時段 |

每筆 allowed_windows 包含 `weekday`、`start_time`、`end_time`；同一天重疊視窗先合併。

#### 輸出合格條件

回傳：

- 全部輸入欄位。
- `plan_id`、`user_id`、`plan_version`。
- `scheduled_minutes`、`remaining_minutes`。
- `created_at`、`updated_at`。

#### 業務規則

- 排程範圍為 start_date 起，至 exam_date 前一日結束。
- 最後一個複習時段可短於 session_minutes，以剛好補足目標。
- exam_task_id 有值時，其截止日期須等於 exam_date；課程有值時須一致。
- 修改考試待辦若會破壞此關聯，回傳 409。
- 修改需求時，既有 sessions 必須仍符合新範圍與需求；否則回傳 409，提示先調整或清空 sessions。
- 刪除計畫時，在同一交易中刪除其 sessions。
- scheduled_minutes 由已保存 sessions 計算，不接受手動指定。

### 2.9 產生複習建議 `POST /study-plans/{id}/generate`

#### 輸入

- Path `id`：本人計畫 ID，必填。
- baseline 不需要 Request body。

#### 輸出合格條件

回傳：

- `plan_id`、`plan_version`。
- `candidates`：每筆含 `title`、`starts_at`、`ends_at`。
- `scheduled_minutes`、`remaining_minutes`。
- `generation_status`：`complete` 或 `partial`。
- `warnings`。

#### 業務規則

- 讀取已保存計畫及最新佔用時段。
- 重新生成時忽略本計畫的舊 sessions，但保留其他計畫的佔用。
- 生成候選結果不會立即取代正式 sessions。
- 時間不足是正常結果：回傳 200、partial 及缺少分鐘。
- 不得產生彼此重疊、超出範圍或與已知事件衝突的候選。
- 若存在未知課表時間，baseline 回傳 409 `SCHEDULE_INCOMPLETE`，不聲稱已生成可安全保存的安排。

### 2.10 確認複習安排 `PUT /study-plans/{id}/sessions`

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `plan_version` | 是 | 必須符合最新計畫版本 |
| `sessions` | 是 | 要保存的完整時段清單，可為空陣列 |

每筆 session 包含 `title`、`starts_at`、`ends_at`。

#### 輸出合格條件

回傳：

- `plan_id`、更新後的 `plan_version`。
- 保存後的 `sessions`，每筆有後端產生的 `session_id`。
- `scheduled_minutes`、`remaining_minutes`。

#### 業務規則

- PUT 代表完整取代指定計畫的 sessions。
- 不影響其他計畫。
- 保存前重新檢查最新行程，不只相信生成當時的結果。
- 驗證日期、可用視窗、單次時長、總分鐘與時段彼此衝突。
- 總分鐘不得超過 target_minutes，可低於目標。
- 標準時段為 session_minutes，最多一個較短的尾段。
- 版本過期或新出現衝突回傳 409。
- 驗證或保存失敗時，原本 sessions 完整保留。
- 空陣列代表明確清空該計畫安排。

### 2.11 調整複習時段

| API | 輸入 | 成功輸出 |
|---|---|---|
| `GET /study-plans/{id}/sessions` | 本人計畫 ID | 200，時段清單、計畫版本及時數摘要 |
| `PATCH /study-sessions/{id}` | `plan_version` 必填，另至少提供 title、starts_at、ends_at 之一 | 200，更新後時段、最新計畫版本及摘要 |
| `DELETE /study-sessions/{id}?plan_version=…` | 本人時段 ID、計畫版本必填 | 204 |

規則：

- PATCH 沿用確認安排的整組驗證，排除正在修改的時段。
- 任何 session 寫入均增加 plan_version。
- 修改與刪除後重新計算時數。
- 刪除不自動重新排程。
- 刪除後前端可再次 GET 取得最新版本與摘要。

### 2.12 修課規劃 `/planned-courses` CRUD

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `target_semester_id` | 是 | 有效目標學期 |
| `course_id` | 是 | 有效課程 |
| `offering_id` | 否 | 有值時必須符合目標學期與課程 |

清單支援 `target_semester_id`。

#### 輸出合格條件

回傳輸入欄位，以及 `planned_course_id`、`user_id`、`created_at`、`updated_at`。

#### 業務規則

- 同一使用者、目標學期、課程不得重複，否則回傳 409。
- 加入規劃不等於選課成功，也不增加已取得學分。
- 先修未符合可以保留為規劃，由檢查 API 提醒。

### 2.13 修課規劃檢查 `POST /planned-courses/check`

#### 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `target_semester_id` | 是 | 有效學期 |
| `items` | 是 | 至少一筆候選課程 |

每筆 items 包含 course_id、選填 offering_id。對傳入整組清單進行檢查，不自動與已保存清單合併。

#### 輸出合格條件

回傳：

- `overall_status`：`passed`、`issues_found`、`needs_confirmation`。
- `duplicate_courses`。
- `prerequisite_checks`。
- `schedule_conflicts`。
- `schedule_check_complete`。
- `warnings`。

#### 業務規則

- 發現重複、缺先修或撞課仍回傳 200，表示檢查已完成。
- 先修課修習中不等於已通過。
- 已通過的相同課程列出提醒，不直接當作新取得學分。
- 先修來源未知時標示 needs_confirmation。
- 未選班別或缺上課時間時，schedule_check_complete=false。
- 撞課檢查包含候選班別彼此，以及目標期間已保存的個人安排。
- 檢查不修改 planned-courses。

### 2.14 畢業規則 `GET /graduation-rules/{rule_set_id}`

#### 輸入

- Path `rule_set_id`：必填。

#### 輸出合格條件

必須包含：

- `rule_set_id`、`version`。
- `department_id`、`admission_year`。
- `sources`：規則來源說明。
- `total_credits_required`。
- `credit_requirements`：分類學分門檻。
- `required_course_ids`。
- `general_education_requirements`。
- `program_requirements`。
- `lecture_requirements`。
- `excluded_conditions`。
- `verification_scope`：第一版判定範圍說明。

#### 業務規則

- 規則不存在回傳 404。
- 不同版本不可直接覆寫成不同內容而保留相同版本號。
- baseline 採團隊草案：133 學分、指定必修、三個學程至少完成兩個、專業講座 10 場、一般講座 12 場。
- 具體清單須引用團隊確認的規則檔，不依課名猜測。
- 結果僅代表符合第一版設定，不代表校方正式認證。

### 2.15 學程清單 `GET /programs`

#### 輸入

| 參數 | 必填 | 規則 |
|---|---|---|
| `rule_set_id` | 是 | 有效規則 ID |

#### 輸出合格條件

每筆包含：

- `program_id`、`name`。
- `rule_set_id`、`list_year`。
- `course_ids`。
- `minimum_passed_courses`。
- `sources`。
- `data_status`：`complete` 或 `needs_confirmation`。

規則：

- 學程是共用條件清單，不含個人完成狀態。
- 課名尚未映射有效 course_id 時，標記 needs_confirmation，不虛構 ID。
- 有效規則沒有學程要求時回傳 200 空清單。

### 2.16 講座場次 `GET /lecture-progress`、`PUT /lecture-progress`

#### PUT 輸入

| 欄位 | 必填 | 規則 |
|---|---|---|
| `professional_count` | 是 | 非負整數或 null |
| `general_count` | 是 | 非負整數或 null |

PUT 完整取代兩類場次，因此兩欄都必須提供。

#### 輸出合格條件

GET 與 PUT 均回傳：

- `user_id`。
- `professional_count`、`general_count`。
- `updated_at`；從未填寫時可為 null。

#### 業務規則

- null 表示尚未提供；0 表示明確完成零場。
- 兩類分開計算，不互相抵用。
- baseline 只保存總數，無法驗證同一場講座是否重複計入。
- 剩餘場次與達標狀態由畢業審核計算，不直接手動設定。

### 2.17 畢業審核 `GET /graduation-progress`

#### 輸入

- 無必填查詢參數。
- 使用目前使用者在 `/me` 的適用規則。

#### 輸出合格條件

回傳：

- `user_id`、`rule_set_id`、`evaluated_at`。
- `overall_status`：`met`、`not_met`、`needs_confirmation`。
- `checks`。
- `credit_allocation`。
- `missing_required_courses`。
- `program_progress`。
- `lecture_progress`。
- `data_errors`。
- `verification_scope`。

每筆 checks 至少包含：

```json
{
  "check_id": "total_credits",
  "name": "總學分",
  "required_value": 133,
  "actual_value": 100,
  "remaining_value": 33,
  "unit": "credits",
  "status": "not_met",
  "message": "尚缺 33 學分"
}
```

#### 業務規則

- 只有已通過的修課紀錄增加已取得學分。
- 同一筆學分不可重複分配不同類別，也不可重複加進總數。
- 學程門數與學分是不同檢核，可以同時受同一課程滿足。
- 修習中與規劃中不得計入已取得學分。
- 剩餘數量最低為 0。
- 缺少資料時 actual_value 或 remaining_value 可為 null，不以 0 冒充。
- 任一項 not_met，整體為 not_met；否則有 needs_confirmation 就為 needs_confirmation；全部 met 才是 met。
- 即使整體 not_met，仍須保留其他待確認項目。
- 尚無適用規則時回傳 200、needs_confirmation 及原因，不擅自套規則。
- 若資料庫本身無法讀取，回傳 500，不偽裝成資料待確認。

### 2.18 首頁摘要 `GET /dashboard`

#### 輸入

| 參數 | 必填 | 規則 |
|---|---|---|
| `date` | 是 | 有效日期 |

#### 輸出合格條件

回傳：

- `date`、`timezone`。
- `today_task_summary`：當日截止待辦的 total、completed。
- `upcoming_tasks`：指定日期起七天內未完成待辦。
- `week_study_summary`：所在週的已安排分鐘與時段數。
- `graduation_summary`：規則、已取得學分、缺必修數及總體狀態。
- `warnings`。

#### 業務規則

- 一週以台北時間週一至週日計算。
- 跨週 session 的分鐘只計入與該週交集的部分。
- 頁面摘要必須使用與詳細 API 相同計算來源。
- 畢業規則未知時相關值為 null 或 needs_confirmation，不填入示範數字。
- 此 API 不另外保存可手動修改的統計值。

### 2.19 校區地圖設定 `GET /campus-maps`

#### 輸入

| 參數 | 必填 | 規則 |
|---|---|---|
| `campus_id` | 否 | 有效校區 ID |

#### 輸出合格條件

每筆回傳：

- `map_id`。
- `campus_id`、`campus_name`。
- `view_name`。
- `image_url`：可供前端載入的靜態資源路徑。
- `alt_text`。
- `sort_order`。

規則：

- baseline 使用既有校區圖片及靜態設定。
- 依 sort_order、map_id 排序。
- 有效校區没有地圖時回傳 200 空清單。
- 不提供 GPS、導航、即時定位或教室座標推估。

---

## 3. 驗收案例

以下全部為「預期結果／未執行」。

| 編號 | 功能與測試輸入／前提 | 預期結果 | 停止位置 |
|---|---|---|---|
| E01 | 新增有效 finished、passed=true 修課紀錄 | 201；再次 GET 可取得；畢業審核納入 | 完成 L6 |
| E02 | grade=50、passed=true | 422，指出矛盾，不保存 | L3 |
| E03 | 重複新增相同課程紀錄 | 409，不重複計入學分 | L3 |
| E04 | 刪除被 timetable-entry 引用的紀錄 | 409，原資料保留 | L3 |
| T01 | 手動建立有效課表與兩筆每週時段 | 201，課表與修課關聯一次建立完整 | 完成 L6 |
| T02 | 某筆 meeting 的 weekday=8 | 422，不建立任何關聯 | L2 |
| T03 | 新課表與已存在私人行程重疊 | 409，回傳衝突，不保存 | L4／L5 |
| T04 | 模擬建立關聯途中資料庫失敗 | 500，全部回滾 | L5 |
| CA01 | 查詢包含課表、行程、複習、待辦的一週 | 200，事件合併且待辦另列，沒有重複課程 | 完成 L6 |
| CA02 | from 晚於 to，或超過 31 天 | 422 | L2 |
| CA03 | 查詢學期範圍以外日期 | 200，不展開該學期課表 | 完成 L6 |
| TA01 | 新增只有 due_date 的待辦 | 201，due_time=null，不產生佔用時段 | 完成 L6 |
| TA02 | PATCH completed=true | 200，完成狀態保存，其他欄位不變 | 完成 L6 |
| TA03 | title 只有空白 | 422，不保存 | L2 |
| PE01 | 新增有效跨日行程且無衝突 | 201，行事曆兩日查詢皆能取得交集事件 | 完成 L6 |
| PE02 | ends_at 早於 starts_at | 422 | L2 |
| PE03 | 行程與已保存複習時段重疊 | 409，衝突來源為 study_session | L4／L5 |
| CF01 | 預覽與課程重疊的候選時間 | 200，has_conflict=true，回傳重疊區間 | 完成 L6 |
| CF02 | 候選開始恰好等於既有事件結束 | 200，該邊界不算衝突 | 完成 L6 |
| CF03 | 課程時間未知 | 200，check_complete=false 並附警告 | 完成 L6 |
| AV01 | 可用 09:00–12:00，佔用 10:00–11:00 | 200，回傳 09:00–10:00、11:00–12:00，共 120 分鐘 | 完成 L6 |
| AV02 | 提供兩筆重疊可用視窗 | 200，先合併，不重複計算分鐘 | 完成 L6 |
| AV03 | 可用區間全部被佔用 | 200，free_slots=[]、total_free_minutes=0 | 完成 L6 |
| SP01 | 建立有效複習需求 | 201，尚未保存 sessions 時 scheduled_minutes=0 | 完成 L6 |
| SP02 | target_minutes=0 或 exam_date 不晚於 start_date | 422 | L2 |
| SP03 | 修改計畫使既有 session 超出新範圍 | 409，計畫與 sessions 均不變 | L3／L4 |
| GE01 | 目標 180 分鐘，有足夠空檔 | 200，候選合計 180、remaining=0，不立即保存 | 完成 L6 |
| GE02 | 目標 180 分鐘，只能排 120 | 200，partial、remaining=60 | 完成 L6 |
| GE03 | 有未知上課時間 | 409 SCHEDULE_INCOMPLETE，不產生可保存候選 | L3／L4 |
| GE04 | 未來外部 AI 回傳重疊或超出範圍時段 | 502，不保存任何候選為正式安排 | L5；AI 擴充案例 |
| SS01 | PUT 有效版本與合法 sessions | 200，僅取代指定計畫安排，回傳新版本 | 完成 L6 |
| SS02 | 生成後有人新增衝突行程，再確認 | 409，舊 sessions 完整保留 | L5 |
| SS03 | 使用過期 plan_version | 409，不覆寫最新資料 | L3／L5 |
| SS04 | PATCH session 到衝突時間 | 409，該時段及摘要不變 | L4／L5 |
| SS05 | DELETE session | 204；再次 GET 顯示時數下降、版本增加 | 完成 L5 |
| PC01 | 新增未重複的修課規劃 | 201；畢業已取得學分不增加 | 完成 L6 |
| PC02 | 重複加入同學期同課程 | 409 | L3 |
| CK01 | 檢查候選清單有重複課程、缺先修 | 200，issues_found 並列出原因，不保存 | 完成 L6 |
| CK02 | 候選沒有開課時間或先修來源未知 | 200，對應檢查待確認，不宣稱全部通過 | 完成 L6 |
| GR01 | 取得存在的畢業規則 | 200，版本、門檻、來源與範圍完整 | 完成 L6 |
| GR02 | 規則 ID 不存在 | 404 | L3 |
| PR01 | 查詢有效規則的學程清單 | 200，課程 ID 與最低通過門數完整 | 完成 L6 |
| PR02 | 缺少 rule_set_id | 422 | L2 |
| LP01 | PUT 專業 10、一般 11 | 200，兩類分別保存 | 完成 L6 |
| LP02 | PUT 其中一類為 -1 或 1.5 | 422，兩類均不更新 | L2 |
| LP03 | GET 尚未填寫的講座場次 | 200，兩類為 null，不冒充 0 | 完成 L6 |
| GP01 | 測試有效採計 100 學分，規則要求 133 | 200，總學分檢核 remaining=33 | 完成 L6 |
| GP02 | 增加修習中或規劃中課程 | 200，已取得學分不增加 | 完成 L6 |
| GP03 | 專業 10、一般 11，門檻為 10／12 | 200，一般講座尚缺 1，不能互相抵用 | 完成 L6 |
| GP04 | 學分分類未知或講座場次為 null | 200，相關檢核為 needs_confirmation，保留原因 | 完成 L6 |
| GP05 | 同一筆選修學分可用於多類 | 200，依規則分配一次，總數不重複增加 | 完成 L6 |
| DB01 | 相同日期查 dashboard 與明細 API | 200，待辦、複習、畢業摘要一致 | 完成 L6 |
| DB02 | date 格式錯誤 | 422 | L2 |
| MP01 | 查詢既有校區地圖 | 200，圖片路径與替代文字完整；前端可載入圖片 | 完成 L6 |
| MP02 | 有效校區沒有設定圖片 | 200，空清單 | 完成 L6 |

### 3.1 所有 CRUD 都要執行的共通案例

| 編號 | 案例 | 預期結果 | 停止位置 |
|---|---|---|---|
| X01 | POST 成功後 GET 詳情／清單 | 新資料一致可讀，清單 count 正確 | 完成 L6 |
| X02 | PATCH 一個欄位 | 其他欄位保持原值 | 完成 L6 |
| X03 | PATCH 空物件或唯讀欄位 | 422，不更新 | L2 |
| X04 | 刪除無關聯限制的資源，再次 GET | DELETE 204，GET 404 | L5／L3 |
| X05 | 查詢或操作不存在 ID | 404 | L3 |
| X06 | 正式版操作另一位使用者的 ID | 404，雙方資料均不變 | L3 |
| X07 | 正式版沒有登入憑證 | 401 | L1 |
| X08 | 模擬保存失敗 | 500，交易回滾 | L5 |
| X09 | Request body 不是合法 JSON | 400 | L2 |
| X10 | 前端傳入 user_id 嘗試指定他人 | 422 | L2 |

正式版身分測試與 AI 擴充案例不列為 baseline 已完成項目。

---

## 4. 選定 baseline 與已知失敗案例

### 4.1 整體版本

採用建議中的 FastAPI＋SQLite：

- 固定測試使用者。
- 共用課程、學期、規則與開課測試資料。
- 各功能共用一套資料庫與時間處理邏輯。
- 先以確定性程式完成排程、衝突與畢業審核。
- 不依賴外部 AI、校務、推播或地圖服務。
- SQLite 寫入採交易，排程保存時重新讀取並驗證佔用資料。
- 測試使用隔離的暫存資料庫，不修改正式資料。

選擇原因：可重複測試資料關聯、計算與保存，不受外部服務穩定性影響；後續 AI 可使用相同輸入輸出契約。

### 4.2 各功能 baseline 與限制

下列「失敗案例」是目前設計無法涵蓋的情境，**不是已執行測試後的失敗結果**。

| 功能 | 最初版本做法與原因 | 一個已知無法涵蓋的案例 |
|---|---|---|
| 修課紀錄 | 手動輸入明確通過狀態，便於驗證採計 | 同課重修後應採哪次成績 |
| 手動課表 | 既有課程＋每週固定時段，減少目錄不一致 | 某一天臨時調課 |
| 日／週行事曆 | 依學期展開固定時段並合併既有安排 | 國定假日應停課但仍被展開 |
| 待辦 | 日期、時間與完成狀態，先支援基本管理 | 每週自動產生重複作業 |
| 私人行程 | 單次起訖，支援跨日 | 每月固定日期的重複行程 |
| 衝突預覽 | 比較時間區間，結果可驗證 | 兩校區相鄰時段沒有交通時間 |
| 空閒時段 | 扣除已知佔用區間 | 未匯入的校外活動無法被扣除 |
| 複習需求 | 每週可用視窗＋總分鐘 | 指定單一日期為特殊休息日 |
| 產生建議 | 日期與時間由早到晚搜尋完整時段，尾段補足分鐘 | 碎片空檔總量足夠，但不足以放入標準單次時長 |
| 確認安排 | 整組驗證並以交易取代，防止部分寫入 | 多台伺服器下的高併發保存尚未驗證 |
| 調整時段 | 手動改時間並重新驗證 | 刪除後自動補排其他空檔 |
| 修課規劃 | 手動選課清單，與已取得學分分開 | 真正向校方選課系統送出選課 |
| 規劃檢查 | 明確先修、重複與已知班別撞課檢查 | 校方允許特殊先修豁免 |
| 畢業規則 | 固定且有版本的第一版規則 | 未支援入學年度的規則判定 |
| 學程 | 固定課程清單與最低門數 | 校方核准替代課程採認 |
| 講座 | 保存兩類總數，操作簡單 | 同一講座被重複計數 |
| 畢業審核 | 依規則檔確定性計算 | 抵免、免修或正式校級其他門檻 |
| 首頁摘要 | 每次由同一原始資料計算 | 大量資料下的效能尚未驗證 |
| 校區地圖 | 靜態圖片，沿用現有素材 | 輸入教室後自動室內導航 |

此外，固定測試身分無法通過真正的多使用者隔離驗收；正式登入完成後必須另外測試。

---

## 5. 標示證據狀態

### 5.1 目前證據

| 項目 | 狀態 |
|---|---|
| API 輸入輸出 | 建議規格 |
| baseline | 設計方案，未實作 |
| 驗收案例 | 預期結果／未執行 |
| HTTP 實際輸出 | 尚無 |
| 自動測試結果 | 尚無 |
| 已知限制 | 設計分析，非實測失敗 |
| 外部 AI 502 案例 | 後續擴充，baseline 不適用 |

### 5.2 待執行指令範例

以下假設本機服务位於 `http://localhost:8000`，並已建立測試課程、學期與使用者。ID 須依測試資料調整。

#### 新增修課紀錄

```bash
curl -i -X POST http://localhost:8000/api/v1/enrollments \
  -H 'Content-Type: application/json' \
  -d '{
    "course_id":"course-demo-001",
    "semester_id":"semester-115-1",
    "enrollment_status":"finished",
    "passed":true,
    "grade":80
  }'
```

預期：201，回傳 enrollment_id 與保存後資料。  
實際輸出：未取得。  
狀態：預期結果／未執行。

#### 新增待辦

```bash
curl -i -X POST http://localhost:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"資料結構作業",
    "type":"assignment",
    "due_date":"2026-10-09"
  }'
```

預期：201，due_time=null、completed=false。  
實際輸出：未取得。  
狀態：預期結果／未執行。

#### 查詢日／週行事曆

```bash
curl -i \
  'http://localhost:8000/api/v1/calendar?from=2026-10-05&to=2026-10-11'
```

預期：200，回傳 events、task_deadlines 與 warnings。  
實際輸出：未取得。  
狀態：預期結果／未執行。

#### 衝突預覽

```bash
curl -i -X POST http://localhost:8000/api/v1/schedule/conflicts \
  -H 'Content-Type: application/json' \
  -d '{
    "starts_at":"2026-10-05T09:30:00+08:00",
    "ends_at":"2026-10-05T10:30:00+08:00"
  }'
```

前提：測試課表存在當日 09:00～10:00 課程。  
預期：200，has_conflict=true，重疊範圍為 09:30～10:00。  
實際輸出：未取得。  
狀態：預期結果／未執行。

#### 產生複習建議

```bash
curl -i -X POST \
  http://localhost:8000/api/v1/study-plans/plan-demo-001/generate
```

前提：已存在有效計畫，且所有佔用時間可確認。  
預期：200，回傳候選時段及不足分鐘；正式 sessions 不變。  
實際輸出：未取得。  
狀態：預期結果／未執行。

#### 保存講座場次

```bash
curl -i -X PUT http://localhost:8000/api/v1/lecture-progress \
  -H 'Content-Type: application/json' \
  -d '{
    "professional_count":10,
    "general_count":11
  }'
```

預期：200，兩類場次分開保存。  
實際輸出：未取得。  
狀態：預期結果／未執行。

#### 查詢畢業進度

```bash
curl -i http://localhost:8000/api/v1/graduation-progress
```

前提：使用者適用測試規則，已有修課及講座測試資料。  
預期：200，依原始紀錄計算；一般講座 11／12 時尚缺 1 場。  
實際輸出：未取得。  
狀態：預期結果／未執行。

### 5.3 實測後的證據格式

每個案例使用下列格式記錄，不只寫「測試通過」：

```text
案例 ID：
程式 commit：
測試日期：
前置資料：
執行指令：
預期 HTTP 狀態：
實際 HTTP 狀態：
實際回應內容：
操作前後資料差異：
流程停止層次及依據：
結果：通過／失敗／未執行
```

流程停止層次須由測試斷言、結構化日誌或交易結果佐證，不能只從 HTTP 狀態碼推測。寫入失敗案例須確認沒有部分保存；生成預覽則須確認沒有修改正式安排。