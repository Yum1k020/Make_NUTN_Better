# 學期、課程與開課查詢 API 規格

> 分支：`feature/course-catalog-api`，由 `feature/user-profile-api` 延伸。本文件區分規格範例與真正執行的證據；原始 JSON 範例不代表校方資料。

## 1. 範圍與共同約定

本文件包含：

| API | 用途 |
|---|---|
| `GET /api/v1/semesters` | 查詢學年度、學期與起訖日期 |
| `GET /api/v1/courses` | 查詢課程目錄 |
| `GET /api/v1/courses/{id}` | 查詢單一課程及先修資料 |
| `GET /api/v1/course-offerings?semester_id=…` | 查詢指定學期的班別、上課時段、校區與教室 |

資料概念：

- **課程**：課名、學分等基本資料。
- **開課**：某門課在某學期開設的班別。
- **上課時段**：某班別每週上課的星期、時間與地點。
- 同一課程可以有多個班別，每個班別可以有多個時段。

共同約定：

- baseline 僅提供共用測試資料查詢，不包含個人修課紀錄。
- ID 使用字串；範例 ID 皆為測試值。
- 學年度使用民國年度整數，例如 `115`。
- 日期使用 `YYYY-MM-DD`，時間使用 `HH:mm`。
- 時區為 `Asia/Taipei`，星期使用 1～7，1 為星期一。
- 未知值使用 `null`；不可將未知先修條件表示為「無先修」。
- baseline 清單一次回傳全部符合資料，不實作分頁。
- 不支援的查詢參數回傳 `422`，避免默默忽略拼字錯誤。
- 本文件的學期日期為展示資料，不代表實際校曆。

## 2. 定義輸入與輸出

### 2.1 GET /semesters

**用途：** 取得學期清單，供課表與修課規劃選擇。

**輸入：**

| 位置 | 欄位 | 型別 | 必填 | 規則 |
|---|---|---|---|---|
| Query | `academic_year` | integer | 否 | 正整數，以民國年度查詢，例如 `115` |

無 Request body。

- 未提供年度：回傳全部已建立的學期。
- 年度格式合法但沒有資料：回傳 `200` 與空清單。
- 排序：學年度由新到舊，同年度依上學期、下學期排列。

**請求範例：**

```http
GET /api/v1/semesters?academic_year=115
```

**成功回應：`200 OK`**

```json
{
  "data": [
    {
      "semester_id": "semester-115-1",
      "academic_year": 115,
      "term": "1",
      "starts_on": "2026-09-01",
      "ends_on": "2027-01-31",
      "timezone": "Asia/Taipei"
    }
  ],
  "meta": {
    "count": 1
  }
}
```

**輸出合格條件：**

| 欄位 | 型別 | 條件 |
|---|---|---|
| `semester_id` | string | 唯一且非空 |
| `academic_year` | integer | 正整數 |
| `term` | string | baseline 為 `"1"` 或 `"2"` |
| `starts_on` | date | 有效日期 |
| `ends_on` | date | 不早於開始日期 |
| `timezone` | string | `Asia/Taipei` |
| `meta.count` | integer | 等於回傳陣列長度 |

### 2.2 GET /courses

**用途：** 查詢課程目錄，提供課名、學分及指定畢業規則下的分類。

**輸入：**

| 位置 | 欄位 | 型別 | 必填 | 規則 |
|---|---|---|---|---|
| Query | `q` | string | 否 | 去除前後空白後為 1～100 字；搜尋課名或課程代碼 |
| Query | `department_id` | string | 否 | 篩選開課系所，必須存在 |
| Query | `rule_set_id` | string | 否 | 指定分類依據，必須存在 |

無 Request body。

- 未提供篩選條件：回傳全部課程。
- 多個條件同時提供：須全部符合。
- `q` 採文字包含比對；英文不區分大小寫。
- 排序固定依 `course_id` 升冪。
- `rule_set_id` 用來提供分類，不會排除尚未分類的課程。
- 不依固定測試使用者的規則暗中套用分類。

**請求範例：**

```http
GET /api/v1/courses?q=資料&rule_set_id=rules-csie-115-v1
```

**成功回應：`200 OK`**

```json
{
  "data": [
    {
      "course_id": "course-demo-001",
      "course_code": null,
      "name": "資料結構",
      "credits": 3,
      "offering_department_id": "dept-csie",
      "classification": {
        "rule_set_id": "rules-csie-115-v1",
        "credit_category": "department_required",
        "status": "classified"
      }
    }
  ],
  "meta": {
    "count": 1
  }
}
```

**輸出合格條件：**

| 欄位 | 型別 | 條件 |
|---|---|---|
| `course_id` | string | 唯一且非空 |
| `course_code` | string 或 null | 不虛構正式代碼 |
| `name` | string | 非空課名 |
| `credits` | number | 非負，可為小數 |
| `offering_department_id` | string 或 null | 已知時對應有效系所 |
| `classification` | object 或 null | 未指定規則時為 null |
| `meta.count` | integer | 等於回傳陣列長度 |

分類處理：

- 指定有效規則且有分類：`status: "classified"`。
- 指定有效規則但尚無分類：`credit_category: null`、`status: "unclassified"`。
- 課程分類依規則版本決定，不是所有學生共用的固定屬性。

`credit_category` 可用值：

```text
general_core
general_domain
general_diverse
college_required
department_required
department_elective
free_elective
```

### 2.3 GET /courses/{id}

**用途：** 取得單一課程的基本資料、分類及先修資訊。

**輸入：**

| 位置 | 欄位 | 型別 | 必填 | 規則 |
|---|---|---|---|---|
| Path | `id` | string | 是 | 要查詢的課程 ID |
| Query | `rule_set_id` | string | 否 | 指定分類依據，必須存在 |

無 Request body。課程 ID 不存在時回傳 `404`。

**成功回應：`200 OK`**

```json
{
  "data": {
    "course_id": "course-demo-001",
    "course_code": null,
    "name": "資料結構",
    "credits": 3,
    "offering_department_id": "dept-csie",
    "classification": {
      "rule_set_id": "rules-csie-115-v1",
      "credit_category": "department_required",
      "status": "classified"
    },
    "prerequisites": {
      "status": "unknown",
      "mode": null,
      "course_ids": null,
      "source": null
    }
  }
}
```

**先修資料合格條件：**

| 情況 | `status` | `mode` | `course_ids` |
|---|---|---|---|
| 已知有先修 | `known` | `all` 或 `any` | 至少一個有效課程 ID |
| 已確認無先修 | `none` | null | `[]` |
| 尚未確認 | `unknown` | null | null |

- `all`：列出的先修課程皆須符合。
- `any`：列出的先修課程至少符合一門。
- `source`：先修規定的來源說明；`known` 與 `none` 必須提供，`unknown` 可為 null。
- 測試先修資料必須明確標註為測試來源。
- 本 API 只回傳先修規定，不判斷某位學生是否符合。
- 清單與詳細查詢在相同 `rule_set_id` 下，基本資料及分類必須一致。

### 2.4 GET /course-offerings

**用途：** 查詢某學期實際建立的開課班別與每週時段。

**輸入：**

| 位置 | 欄位 | 型別 | 必填 | 規則 |
|---|---|---|---|---|
| Query | `semester_id` | string | 是 | 必須存在的學期 ID |
| Query | `course_id` | string | 否 | 必須存在的課程 ID，用於篩選 |

無 Request body。

- 缺少學期或參照 ID 無效：回傳 `422`。
- 學期存在但沒有開課：回傳 `200` 與空清單。
- 排序固定依 `course_id`、`offering_id` 升冪。
- 各班別內的時段依星期、開始時間排序。

**請求範例：**

```http
GET /api/v1/course-offerings?semester_id=semester-115-1
```

**成功回應：`200 OK`**

```json
{
  "data": [
    {
      "offering_id": "offering-demo-001",
      "course_id": "course-demo-001",
      "course_name": "資料結構",
      "semester_id": "semester-115-1",
      "section_name": "A班",
      "schedule_status": "scheduled",
      "class_meetings": [
        {
          "meeting_id": "meeting-demo-001",
          "weekday": 1,
          "start_time": "09:00",
          "end_time": "10:00",
          "campus_id": "campus-demo",
          "location": "測試教室 A"
        },
        {
          "meeting_id": "meeting-demo-002",
          "weekday": 3,
          "start_time": "10:00",
          "end_time": "12:00",
          "campus_id": "campus-demo",
          "location": "測試教室 A"
        }
      ]
    }
  ],
  "meta": {
    "count": 1
  }
}
```

**輸出合格條件：**

| 欄位 | 型別 | 條件 |
|---|---|---|
| `offering_id` | string | 唯一開課識別碼 |
| `course_id` | string | 對應存在的課程 |
| `course_name` | string | 與課程目錄一致 |
| `semester_id` | string | 必須等於查詢學期 |
| `section_name` | string 或 null | 未提供班別時為 null |
| `schedule_status` | string | baseline 為 `scheduled` 或 `unknown` |
| `class_meetings` | array | scheduled 時至少一筆；unknown 時為空陣列 |
| `meta.count` | integer | 計算開課筆數，不是上課時段數 |

每筆 `class_meetings` 必須包含：

- `meeting_id`：唯一字串。
- `weekday`：1～7 的整數。
- `start_time`、`end_time`：有效時間，結束晚於開始。
- `campus_id`：有效校區 ID 或 null。
- `location`：地點文字或 null。

baseline 僅支援同一天內的每週固定時段。時間尚未確認的開課標示為 `unknown`，前端不得將其解讀成「已確認沒有衝突」。

## 3. 共用錯誤格式與流程層次

**錯誤格式：**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "查詢參數不合法",
    "fields": [
      {
        "field": "semester_id",
        "reason": "此欄位為必填"
      }
    ]
  }
}
```

- `422`：缺少必填參數、格式錯誤或篩選參照 ID 無效。
- `404`：`GET /courses/{id}` 指定的課程不存在。
- `500`：資料庫讀取失敗或後端資料不符合輸出契約。
- 非欄位類錯誤的 `fields` 回傳空陣列。
- 不回傳資料庫連線資訊或內部堆疊。

**流程層次：**

| 層次 | 工作 |
|---|---|
| L1 | 解析路徑與查詢參數，檢查必填、型別及允許值 |
| L2 | 檢查系所、規則、學期等參照資料是否存在 |
| L3 | 查詢課程、學期、開課與時段 |
| L4 | 組成回應，檢查關聯、欄位與資料一致性 |

這些都是查詢 API，各層均不應修改資料。L2 可能讀取資料庫以確認參照資料；「停在 L2」不代表完全沒有資料庫存取。

## 4. 設計驗收案例

### 4.1 學期清單

| 編號 | 測試輸入／前提 | 預期結果 | 停止位置 | 證據狀態 |
|---|---|---|---|---|
| S01 | 不帶查詢參數 | `200`，回傳全部學期，排序正確，count 一致 | 完成 L4 | 實測通過，見第 6 節 |
| S02 | `academic_year=115` | `200`，只回傳 115 學年度資料 | 完成 L4 | 實測通過，見第 6 節 |
| S03 | `academic_year=abc` | `422`，指出年度格式錯誤 | L1 | 實測通過，見第 6 節 |
| S04 | 正整數年度，但沒有資料 | `200`，data 為空陣列，count 為 0 | 完成 L4 | 實測通過，見第 6 節 |
| S05 | 模擬資料庫內學期結束早於開始 | `500`，不回傳不合法日期資料 | L4 | 實測通過，見第 6 節 |

### 4.2 課程清單與詳細資料

| 編號 | 測試輸入／前提 | 預期結果 | 停止位置 | 證據狀態 |
|---|---|---|---|---|
| C01 | 不帶查詢參數 | `200`，回傳全部課程，classification 為 null | 完成 L4 | 實測通過，見第 6 節 |
| C02 | `q=資料` | `200`，只回傳課名或代碼含「資料」的課程 | 完成 L4 | 實測通過，見第 6 節 |
| C03 | 搜尋文字沒有任何匹配 | `200`，空清單，不回傳 404 | 完成 L4 | 實測通過，見第 6 節 |
| C04 | `q` 只有空白 | `422`，指出搜尋文字不可為空 | L1 | 實測通過，見第 6 節 |
| C05 | `department_id=unknown` | `422`，指出系所不存在 | L2 | 實測通過，見第 6 節 |
| C06 | `rule_set_id=unknown` | `422`，指出規則不存在 | L2 | 實測通過，見第 6 節 |
| C07 | 有效規則，但某課程沒有分類 | `200`，保留該課程，分類值為 null、狀態為 unclassified | 完成 L4 | 實測通過，見第 6 節 |
| C08 | 詳細查詢有效課程 ID | `200`，回傳基本資料、分類及先修物件 | 完成 L4 | 實測通過，見第 6 節 |
| C09 | 詳細查詢不存在的課程 ID | `404`，錯誤碼 COURSE_NOT_FOUND | L3 | 實測通過，見第 6 節 |
| C10 | 課程先修尚未確認 | `200`，status 為 unknown，course_ids 為 null | 完成 L4 | 實測通過，見第 6 節 |
| C11 | 課程已確認無先修 | `200`，status 為 none、course_ids 為空陣列，附來源 | 完成 L4 | 實測通過，見第 6 節 |
| C12 | 測試資料有兩門先修且 mode=all | `200`，完整回傳兩個有效 ID、all 與來源 | 完成 L4 | 實測通過，見第 6 節 |
| C13 | 相同規則下查清單與詳細 | 課名、學分、分類一致 | 完成 L4 | 實測通過，見第 6 節 |
| C14 | 同一課程在兩套測試規則下分類不同 | 各回傳對應分類，不交叉套用 | 完成 L4 | 實測通過，見第 6 節 |

### 4.3 學期開課

| 編號 | 測試輸入／前提 | 預期結果 | 停止位置 | 證據狀態 |
|---|---|---|---|---|
| O01 | 指定有效且有開課的學期 | `200`，所有開課均屬於指定學期 | 完成 L4 | 實測通過，見第 6 節 |
| O02 | 未提供 semester_id | `422`，指出必填參數缺漏 | L1 | 實測通過，見第 6 節 |
| O03 | `semester_id=unknown` | `422`，指出學期不存在 | L2 | 實測通過，見第 6 節 |
| O04 | 有效學期，但没有開課 | `200`，空清單，count 為 0 | 完成 L4 | 實測通過，見第 6 節 |
| O05 | 學期有效，`course_id=unknown` | `422`，指出課程不存在 | L2 | 實測通過，見第 6 節 |
| O06 | 一門課同學期開設 A、B 兩班 | `200`，兩筆不同 offering_id，不合併班別 | 完成 L4 | 實測通過，見第 6 節 |
| O07 | 同一班別每週有兩個時段 | `200`，一筆開課內含兩筆時段，count 為 1 | 完成 L4 | 實測通過，見第 6 節 |
| O08 | 時段已知、教室未知 | `200`，保留時間，location 為 null | 完成 L4 | 實測通過，見第 6 節 |
| O09 | 開課存在，但時間未確認 | `200`，schedule_status 為 unknown，時段為空陣列 | 完成 L4 | 實測通過，見第 6 節 |
| O10 | 模擬資料庫內 weekday=8 或結束早於開始 | `500`，不回傳無效時段 | L4 | 實測通過，見第 6 節 |

### 4.4 共通錯誤

| 編號 | 測試輸入／前提 | 預期結果 | 停止位置 | 證據狀態 |
|---|---|---|---|---|
| X01 | 任一 API 傳入不支援的查詢參數 | `422`，指出參數名稱 | L1 | 實測通過，見第 6 節 |
| X02 | 模擬資料庫查詢失敗 | `500`，回傳共用錯誤格式，不洩漏內部資訊 | L2 或 L3，依失敗操作 | 實測通過，見第 6 節 |

**502 的適用性：**

baseline 沒有 AI 或外部校務服務，不存在「生成結果驗證失敗」，因此不設定 502 驗收案例。自身資料或輸出契約錯誤使用 500；未來增加外部串接時，再設計上游服務失敗的處理。

## 5. 選定 baseline

**實作 baseline：Flask＋SQLite，固定測試資料，四個唯讀端點。** 原始規格寫 FastAPI；依使用者先前「統一 Flask」的決策調整框架，沿用既有 /me 的 app 與資料庫，不改動本文件的 API 輸入／輸出契約。

| 項目 | 做法 |
|---|---|
| 學期 | 預設數筆學期，含至少一個沒有開課的學期 |
| 課程 | 預設課名、學分、系所，正式代碼未知時為 null |
| 分類 | 建立規則—課程分類對照，包含未分類案例 |
| 先修 | 建立 known、none、unknown 三種測試資料 |
| 開課 | 建立同課多班、同班多時段及未知時間的案例 |
| 日期與時間 | 存入明確測試值，不從學年度推算校曆 |
| 測試資料庫 | 每個測試使用隔離的暫存 SQLite |
| 外部服務 | 不接校務系統、AI 或導航服務 |
| 查詢方式 | 簡單文字搜尋及固定排序，暫不分頁 |

**選擇原因：**

先驗證「課程、學期開課、上課時段」的關聯，以及分類和先修資料的正確表達。固定資料讓測試可重複執行，也讓前端能先串接，不必等待校方資料接口。

**已知無法滿足的案例：臨時停課或單次調課。**

- 前提：某班原訂每週一 09:00 上課，其中一天臨時改到週二。
- 期待功能：指定日期的課表能顯示改後時間。
- baseline 限制：只有每週固定時段，沒有單次例外資料，因此無法表達此次異動。
- 後續方向：新增停課／調課例外資料，並在日期化課表 API 套用。
- 證據狀態：**設計上已知限制／未執行，並非實測失敗。**


### 5.1 本次實作與相容性

- 共用既有 SQLite 連線與 `ME_DATABASE` 設定；不新增第三方依賴，也不新增另一個 server。
- `init-db` 會為原本只有 `id` 的 `semesters` 加入學年度、學期、日期及時區欄位，再建立課程、規則分類、先修關聯、開課、時段與校區資料表。升級不刪除使用者或學期列，既有 `/me` 的外鍵與資料保留。
- 已知測試學期的 metadata 全部為 null 時才填入明確的展示值；不覆寫已存在的 metadata，不根據年度猜校曆。其他自行新增但不完整的資料不會被自動捏造，輸出檢查會回傳 500。
- 初始化重跑採 INSERT OR IGNORE，不覆寫已存在的課名或個人資料。部署既有資料庫前應先備份；本次僅在隔離測試資料庫驗證升級，沒有更動使用者的開發資料庫。
- API 在 L1 檢查未知參數、重複參數、空 ID、年度與 q 長度；不接受 GET body（422）。重複參數不採用第一個或最後一個值，直接回 422。
- 年度接受僅 ASCII 數字的正整數（前置零允許），不接受符號、浮點、空白或布林文字；合法但非常大的年度同樣回傳空清單，不產生整數溢位。
- ID 精確比對，不自行修剪。q 去除前後空白後用 `instr(lower(...), lower(?))` 搜尋，英文不分大小寫；`%`、`_` 為一般字元，不作萬用字元。所有資料值使用 SQL 綁定參數。
- L2 檢查有效參照後，使用同一個讀取交易完成 L3、L4。課程詳情同時傳入無效規則與不存在課程 ID 時，先回 L2 的 422；規則有效後才查詢課程並可能回 404。
- 各請求啟用 SQLite `PRAGMA query_only=ON`；端點不建表、不載入種子、不寫個人資料。每筆自動化 API 測試另驗證資料庫檔案 SHA-256 前後一致、SQL trace 沒有寫入操作。
- 回應先經 Marshmallow 欄位與跨欄位驗證，再序列化：檢查日期順序、時間有效性、星期範圍、非負有限學分、分類狀態、先修來源及關聯、開課排程狀態與時段一致性。資料庫錯誤與壞資料只在服務端記錄詳情，HTTP 回共用 JSON 500。
- `meta.count` 計算回傳項目數；先修 ID 以字串升冪穩定排序；時段若星期／開始時間相同，以 meeting_id 作最後排序依據。
- 既有 1 MiB 請求上限由 Flask 控制；413 等框架層行為本次未驗收，不列為通過。

### 5.2 固定測試資料

| 類型 | 資料與目的 |
|---|---|
| 學期 | `semester-115-1`、`semester-115-2`、`semester-114-2`；後兩個沒有開課。所有日期皆為展示值。 |
| 系所 | 沿用 `dept-csie`、`dept-demo`；部分課程系所未知為 null。 |
| 分類規則 | 沿用 `rules-csie-115-v1`，新增 `rules-demo-114-v1`（映射 dept-demo／114）。不新增 dept-csie／114 或 dept-demo／115 映射，保留 /me 無規則情境。 |
| 課程 | `course-demo-001`～`006`：資料結構、程式設計、離散數學、進階資料分析、跨域專題、探索課程。含 0 與 2.5 學分，部分代碼為 null。`DEMO-*` 明確為測試代碼。 |
| 先修 | 001、006 unknown；002、003 none；004 known/all；005 known/any；已確認的資料均附「測試來源」文字。 |
| 分類差異 | 001 在資工規則為 department_required，在第二套規則為 free_elective；沒有分類的課程仍保留。 |
| 開課 | 115-1 學期共 4 筆：001 的 A/B 班、002 的未知時段開課、004 的單班雙時段開課。 |
| 時段 | 共 5 筆，包含同班不同星期、同日不同時間、教室／校區未知；`campus-demo` 不是正式校方 ID。 |

這些資料不會自動導入根目錄的畢業規則 JSON，也不會將前端 localStorage 視為正式資料來源。

## 6. 真正執行的測試證據

- 日期：`2026-09-24T09:55:47.749903+08:00` 至 `2026-09-24T09:55:49.225082+08:00`（Asia/Taipei）。
- 基底 commit：`88c2beb73bca97d67ed32f0b65b7b85ec2a8435d`；測試時分支為 `feature/course-catalog-api`，新程式尚未提交，不能宣稱基底 commit 已包含本次實作。
- 來源 SHA-256 指紋：`382a6e1365cf9872ea0a3180bb3245d164c585889fe8750e33bc1d6bdfd0e227`。逐檔雜湊、套件版本及執行參數見 [完整證據 JSON](evidence/catalog-results.json)。
- 執行命令：`./scripts/test-backend.sh --evidence=../docs/api/evidence/catalog-results.json`，退出碼 `0`。
- 結果：**124 passed、2 skipped**。其中新課程查詢測試 **82 passed**；既有 /me 與環境回歸測試 **42 passed、2 skipped**。skip 是尚未實作的登入與多使用者隔離，不是查詢 API 通過證據。
- 環境：Python 3.12.14、SQLite 3.53.1；依賴：`{"Flask": "3.1.3", "flask-smorest": "0.47.0", "marshmallow": "4.3.1", "pytest": "9.1.1"}`。

實際 pytest 摘要：

```text
124 passed, 2 skipped in 1.47s
```

第一輪為 `1 failed, 123 passed, 2 skipped`，保留於 [第一次執行紀錄](evidence/catalog-initial-results.json)。失敗原因是 X01 的開課測試同時把 query 放在 URL 與 Flask test client 的 query_string，引發測試建構錯誤，該子案例沒有送出 HTTP，不能標為通過。修正測試後重跑全部測試，以下狀態僅採最後成功執行的紀錄。

每個測試重新建立暫存 SQLite。JSON 的 `setup_sql` 為前置資料或故障注入，`records` 保留實際查詢、HTTP 狀態碼、完整 response body、停止層次的預期、SQL trace 及資料庫前後雜湊。L1 案例另斷言沒有 SQL；X02 使用 SQLite authorizer 拒絕 SQLITE_READ，以實際 SQLite 查詢錯誤驗證 500。這些操作不破壞開發資料庫。

### 6.1 各測試實際結果

下表輸出為摘要；完整輸入與回應內容以證據 JSON 的相同 test ID 查閱。包含多次請求的案例列第一筆實際呼叫，後續比對與回應同樣收錄於 JSON。

| 測試 ID | 主要實際輸入 | 實際狀態碼 | 實際輸出摘要 | 結果 |
|---|---|---|---|---|
| `test_S01_all_semesters_sorted` | `/api/v1/semesters ` | 200 | `count=3; IDs=["semester-115-1","semester-115-2","semester-114-2"]` | 通過 |
| `test_S02_filter_year` | `/api/v1/semesters {"academic_year":"115"}` | 200 | `count=2; IDs=["semester-115-1","semester-115-2"]` | 通過 |
| `test_S03_invalid_year[abc]` | `/api/v1/semesters {"academic_year":"abc"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[0]` | `/api/v1/semesters {"academic_year":"0"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[-1]` | `/api/v1/semesters {"academic_year":"-1"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[115.0]` | `/api/v1/semesters {"academic_year":"115.0"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[true]` | `/api/v1/semesters {"academic_year":"true"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[]` | `/api/v1/semesters {"academic_year":""}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[ 115]` | `/api/v1/semesters {"academic_year":" 115"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S03_invalid_year[+115]` | `/api/v1/semesters {"academic_year":"+115"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"必須為正整數民國學年度"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_S04_year_without_data[999]` | `/api/v1/semesters {"academic_year":"999"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_S04_year_without_data[9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999]` | `/api/v1/semesters {"academic_year":"9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_S05_invalid_stored_dates[2020-01-01]` | `/api/v1/semesters ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_S05_invalid_stored_dates[2027-02-30]` | `/api/v1/semesters ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_S05_invalid_stored_dates[2027-1-31]` | `/api/v1/semesters ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_C01_all_courses_without_implicit_rule` | `/api/v1/courses ` | 200 | `count=6; IDs=["course-demo-001","course-demo-002","course-demo-003","course-demo-004","course-demo-005","course-demo-006"]` | 通過 |
| `test_C02_search_name_or_code[\u8cc7\u6599-ids0]` | `/api/v1/courses {"q":"資料"}` | 200 | `count=2; IDs=["course-demo-001","course-demo-004"]` | 通過 |
| `test_C02_search_name_or_code[ demo-prog -ids1]` | `/api/v1/courses {"q":" demo-prog "}` | 200 | `count=1; IDs=["course-demo-002"]` | 通過 |
| `test_C03_no_matches_literal_search[\u4e0d\u5b58\u5728]` | `/api/v1/courses {"q":"不存在"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_C03_no_matches_literal_search[%]` | `/api/v1/courses {"q":"%"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_C03_no_matches_literal_search[_]` | `/api/v1/courses {"q":"_"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_C03_no_matches_literal_search[' OR 1=1 --]` | `/api/v1/courses {"q":"' OR 1=1 --"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_C04_invalid_search[]` | `/api/v1/courses {"q":""}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"q","reason":"搜尋文字去除前後空白後須為 1～100 字"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_C04_invalid_search[  ]` | `/api/v1/courses {"q":"  "}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"q","reason":"搜尋文字去除前後空白後須為 1～100 字"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_C04_invalid_search[\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57\u5b57]` | `/api/v1/courses {"q":"字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字字"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"q","reason":"搜尋文字去除前後空白後須為 1～100 字"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_C05_invalid_department` | `/api/v1/courses {"department_id":"unknown"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"department_id","reason":"系所不存在"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_C06_invalid_rule[courses]` | `/api/v1/courses {"rule_set_id":"unknown"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"rule_set_id","reason":"規則不存在"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_C06_invalid_rule[courses/course-demo-001]` | `/api/v1/courses/course-demo-001 {"rule_set_id":"unknown"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"rule_set_id","reason":"規則不存在"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_C07_unclassified_retained` | `/api/v1/courses {"rule_set_id":"rules-csie-115-v1"}` | 200 | `count=6; IDs=["course-demo-001","course-demo-002","course-demo-003","course-demo-004","course-demo-005","course-demo-006"]` | 通過 |
| `test_C08_detail` | `/api/v1/courses/course-demo-001 {"rule_set_id":"rules-csie-115-v1"}` | 200 | `{"data":{"classification":{"credit_category":"department_required","rule_set_id":"rules-csie-115-v1","status":"classified"},"course_code":null,"course_id":"course-demo-001","credits":3.0,"name":"資料結構","offering_department_id":"dept-csie","prerequisites":{"course_ids":null,"mode":null,"source":null,"status":"unknown"}}}` | 通過 |
| `test_C09_missing_course` | `/api/v1/courses/unknown ` | 404 | `{"error":{"code":"COURSE_NOT_FOUND","fields":[],"message":"課程不存在"}}` | 通過 |
| `test_C10_unknown_prerequisites` | `/api/v1/courses/course-demo-001 ` | 200 | `{"data":{"classification":null,"course_code":null,"course_id":"course-demo-001","credits":3.0,"name":"資料結構","offering_department_id":"dept-csie","prerequisites":{"course_ids":null,"mode":null,"source":null,"status":"unknown"}}}` | 通過 |
| `test_C11_confirmed_no_prerequisites` | `/api/v1/courses/course-demo-002 ` | 200 | `{"data":{"classification":null,"course_code":"DEMO-PROG","course_id":"course-demo-002","credits":3.0,"name":"程式設計","offering_department_id":"dept-csie","prerequisites":{"course_ids":[],"mode":null,"source":"測試來源：合成先修規定，非校方正式規定","status":"none"}}}` | 通過 |
| `test_C12_known_prerequisites[course-demo-004-all]` | `/api/v1/courses/course-demo-004 ` | 200 | `{"data":{"classification":null,"course_code":null,"course_id":"course-demo-004","credits":3.0,"name":"進階資料分析","offering_department_id":"dept-csie","prerequisites":{"course_ids":["course-demo-002","course-demo-003"],"mode":"all","source":"測試來源：合成先修規定，非校方正式規定","status":"known"}}}` | 通過 |
| `test_C12_known_prerequisites[course-demo-005-any]` | `/api/v1/courses/course-demo-005 ` | 200 | `{"data":{"classification":null,"course_code":"DEMO-ANY","course_id":"course-demo-005","credits":0.0,"name":"跨域專題","offering_department_id":"dept-demo","prerequisites":{"course_ids":["course-demo-002","course-demo-003"],"mode":"any","source":"測試來源：合成先修規定，非校方正式規定","status":"known"}}}` | 通過 |
| `test_C13_list_detail_consistency[None]` | `/api/v1/courses ` | 200 | `count=6; IDs=["course-demo-001","course-demo-002","course-demo-003","course-demo-004","course-demo-005","course-demo-006"]` | 通過 |
| `test_C13_list_detail_consistency[rules-csie-115-v1]` | `/api/v1/courses {"rule_set_id":"rules-csie-115-v1"}` | 200 | `count=6; IDs=["course-demo-001","course-demo-002","course-demo-003","course-demo-004","course-demo-005","course-demo-006"]` | 通過 |
| `test_C13_list_detail_consistency[rules-demo-114-v1]` | `/api/v1/courses {"rule_set_id":"rules-demo-114-v1"}` | 200 | `count=6; IDs=["course-demo-001","course-demo-002","course-demo-003","course-demo-004","course-demo-005","course-demo-006"]` | 通過 |
| `test_C14_rule_specific_classification` | `/api/v1/courses/course-demo-001 {"rule_set_id":"rules-csie-115-v1"}` | 200 | `{"data":{"classification":{"credit_category":"department_required","rule_set_id":"rules-csie-115-v1","status":"classified"},"course_code":null,"course_id":"course-demo-001","credits":3.0,"name":"資料結構","offering_department_id":"dept-csie","prerequisites":{"course_ids":null,"mode":null,"source":null,"status":"unknown"}}}` | 通過 |
| `test_O01_offerings_for_semester` | `/api/v1/course-offerings {"semester_id":"semester-115-1"}` | 200 | `count=4; IDs=["offering-demo-001","offering-demo-002","offering-demo-003","offering-demo-004"]` | 通過 |
| `test_O02_missing_semester` | `/api/v1/course-offerings ` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"semester_id","reason":"此欄位為必填"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_O03_invalid_semester` | `/api/v1/course-offerings {"semester_id":"unknown"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"semester_id","reason":"學期不存在"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_O04_semester_without_offerings` | `/api/v1/course-offerings {"semester_id":"semester-115-2"}` | 200 | `count=0; IDs=[]` | 通過 |
| `test_O05_invalid_course` | `/api/v1/course-offerings {"semester_id":"semester-115-1","course_id":"unknown"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"course_id","reason":"課程不存在"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_O06_multiple_sections` | `/api/v1/course-offerings {"semester_id":"semester-115-1","course_id":"course-demo-001"}` | 200 | `count=2; IDs=["offering-demo-001","offering-demo-002"]` | 通過 |
| `test_O07_multiple_meetings_count_offerings` | `/api/v1/course-offerings {"semester_id":"semester-115-1","course_id":"course-demo-004"}` | 200 | `count=1; IDs=["offering-demo-004"]` | 通過 |
| `test_O08_unknown_location` | `/api/v1/course-offerings {"semester_id":"semester-115-1","course_id":"course-demo-001"}` | 200 | `count=2; IDs=["offering-demo-001","offering-demo-002"]` | 通過 |
| `test_O09_unknown_schedule` | `/api/v1/course-offerings {"semester_id":"semester-115-1","course_id":"course-demo-002"}` | 200 | `count=1; IDs=["offering-demo-003"]` | 通過 |
| `test_O10_invalid_stored_meeting[weekday-8]` | `/api/v1/course-offerings {"semester_id":"semester-115-1"}` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_O10_invalid_stored_meeting[weekday-1.5]` | `/api/v1/course-offerings {"semester_id":"semester-115-1"}` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_O10_invalid_stored_meeting[end_time-08:00]` | `/api/v1/course-offerings {"semester_id":"semester-115-1"}` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_O10_invalid_stored_meeting[end_time-09:00]` | `/api/v1/course-offerings {"semester_id":"semester-115-1"}` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_O10_invalid_stored_meeting[start_time-25:00]` | `/api/v1/course-offerings {"semester_id":"semester-115-1"}` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_X01_unknown_query[semesters]` | `/api/v1/semesters {"typo":"value"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"typo","reason":"不支援的查詢參數"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_X01_unknown_query[courses]` | `/api/v1/courses {"typo":"value"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"typo","reason":"不支援的查詢參數"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_X01_unknown_query[courses/course-demo-001]` | `/api/v1/courses/course-demo-001 {"typo":"value"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"typo","reason":"不支援的查詢參數"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_X01_unknown_query[course-offerings?semester_id=semester-115-1]` | `/api/v1/course-offerings {"typo":"value","semester_id":"semester-115-1"}` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"typo","reason":"不支援的查詢參數"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_X02_database_read_failure[semesters]` | `/api/v1/semesters ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_X02_database_read_failure[courses]` | `/api/v1/courses ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_X02_database_read_failure[courses/course-demo-001]` | `/api/v1/courses/course-demo-001 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_X02_database_read_failure[course-offerings?semester_id=semester-115-1]` | `/api/v1/course-offerings?semester_id=semester-115-1 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_X02_database_read_failure[courses?department_id=dept-csie]` | `/api/v1/courses?department_id=dept-csie ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E01_combined_filters` | `/api/v1/courses {"q":"資料","department_id":"dept-csie","rule_set_id":"rules-csie-115-v1"}` | 200 | `count=2; IDs=["course-demo-001","course-demo-004"]` | 通過 |
| `test_E02_repeated_query_rejected[semesters-academic_year]` | `/api/v1/semesters [["academic_year","115"],["academic_year","115"]]` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"academic_year","reason":"查詢參數不可重複"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_E02_repeated_query_rejected[courses-q]` | `/api/v1/courses [["q","115"],["q","115"]]` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"q","reason":"查詢參數不可重複"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_E02_repeated_query_rejected[courses/course-demo-001-rule_set_id]` | `/api/v1/courses/course-demo-001 [["rule_set_id","115"],["rule_set_id","115"]]` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"rule_set_id","reason":"查詢參數不可重複"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_E02_repeated_query_rejected[course-offerings-semester_id]` | `/api/v1/course-offerings [["semester_id","115"],["semester_id","115"]]` | 422 | `{"error":{"code":"VALIDATION_ERROR","fields":[{"field":"semester_id","reason":"查詢參數不可重複"}],"message":"查詢參數不合法"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE courses SET credits=-1-courses]` | `/api/v1/courses ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE courses SET name=''-courses]` | `/api/v1/courses ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE courses SET offering_department_id='missing'-courses]` | `/api/v1/courses ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE courses SET prerequisite_source=NULL WHERE course_id='course-demo-002'-courses/course-demo-002]` | `/api/v1/courses/course-demo-002 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[DELETE FROM course_prerequisites WHERE course_id='course-demo-004'-courses/course-demo-004]` | `/api/v1/courses/course-demo-004 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE course_prerequisites SET prerequisite_id='missing' WHERE prerequisite_id='course-demo-002'-courses/course-demo-004]` | `/api/v1/courses/course-demo-004 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE course_classifications SET credit_category='invalid'-courses?rule_set_id=rules-csie-115-v1]` | `/api/v1/courses?rule_set_id=rules-csie-115-v1 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE course_offerings SET schedule_status='unknown' WHERE offering_id='offering-demo-001'-course-offerings?semester_id=semester-115-1]` | `/api/v1/course-offerings?semester_id=semester-115-1 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE course_offerings SET schedule_status='scheduled' WHERE offering_id='offering-demo-003'-course-offerings?semester_id=semester-115-1]` | `/api/v1/course-offerings?semester_id=semester-115-1 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE class_meetings SET campus_id='missing'-course-offerings?semester_id=semester-115-1]` | `/api/v1/course-offerings?semester_id=semester-115-1 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E03_invalid_stored_contract[UPDATE course_offerings SET course_id='missing'-course-offerings?semester_id=semester-115-1]` | `/api/v1/course-offerings?semester_id=semester-115-1 ` | 500 | `{"error":{"code":"INTERNAL_ERROR","fields":[],"message":"無法讀取查詢資料"}}` | 通過 |
| `test_E04_init_idempotent_preserves_changes` | `/api/v1/courses/course-demo-001 ` | 200 | `{"data":{"classification":null,"course_code":null,"course_id":"course-demo-001","credits":3.0,"name":"保留自訂名稱","offering_department_id":"dept-csie","prerequisites":{"course_ids":null,"mode":null,"source":null,"status":"unknown"}}}` | 通過 |
| `test_E05_upgrade_original_profile_database` | 初始化升級或 OpenAPI 驗證，見 evidence records | 非單一 HTTP 案例 | `[{"legacy_schema_commit":"88c2beb","init_output":"Initialized SQLite baseline (existing profiles preserved).\n","profile_before":{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}},"profile_after":{"data":{"admission_year":115,"current_semester_id":"semester-115-1","department_id":"dept-csie","profile_complete":true,"rule_set_id":"rules-csie-115-v1","rule_status":"matched","user_id":"user-demo-001"}}}]` | 通過 |
| `test_E06_openapi` | 初始化升級或 OpenAPI 驗證，見 evidence records | 非單一 HTTP 案例 | `[{"openapi_paths_checked":["/api/v1/semesters","/api/v1/courses","/api/v1/courses/{course_id}","/api/v1/course-offerings"],"offering_query_parameters":[{"in":"query","name":"semester_id","required":true,"schema":{"type":"string","minLength":1}},{"in":"query","name":"course_id","required":false,"schema":{"type":"string","minLength":1}}]}]` | 通過 |
| `test_E07_real_http` | `http://127.0.0.1:57548/api/v1/semesters ` | 200 | `count=3; IDs=["semester-115-1","semester-115-2","semester-114-2"]` | 通過 |

### 6.2 額外驗證的範圍

| ID | 目的 | 實測結果 |
|---|---|---|
| E01 | 多個搜尋條件同時符合；有效課程但該學期無開課 | 200，篩選正確或空清單 |
| E02 | 四支 API 重複 query key | 422，停 L1，無 SQL |
| E03 | 負學分、空課名、壞系所／先修／校區／課程外鍵、不合法分類、排程狀態不一致等 11 組壞資料 | 500，停 L4，不輸出壞資料，資料庫未被修改 |
| E04 | 重複 init-db | 成功；保留自訂課名與 /me 個人資料 |
| E05 | 從 88c2beb 版本 schema 快照建立舊資料庫後升級 | 個人資料前後一致；新學期查詢 200；foreign_key_check 無違規 |
| E06 | OpenAPI 四支 GET、狀態碼、必填 semester_id | 結構斷言通過 |
| E07 | 啟動真正的本機 HTTP server，依序呼叫四支 API | 全部 200；回應與 test client 相同 |

### 6.3 真實 HTTP 紀錄

此段來自 E07 實際啟動的本機服務；使用隨機可用 port，測試完成後已停止程序。不是手寫範例，也不是僅由函式推測的結果。

```json
[
  {
    "transport": "real HTTP",
    "url": "http://127.0.0.1:57548/api/v1/semesters",
    "actual_status": 200,
    "actual_body": {
      "data": [
        {
          "academic_year": 115,
          "ends_on": "2027-01-31",
          "semester_id": "semester-115-1",
          "starts_on": "2026-09-01",
          "term": "1",
          "timezone": "Asia/Taipei"
        },
        {
          "academic_year": 115,
          "ends_on": "2027-06-30",
          "semester_id": "semester-115-2",
          "starts_on": "2027-02-01",
          "term": "2",
          "timezone": "Asia/Taipei"
        },
        {
          "academic_year": 114,
          "ends_on": "2026-06-30",
          "semester_id": "semester-114-2",
          "starts_on": "2026-02-01",
          "term": "2",
          "timezone": "Asia/Taipei"
        }
      ],
      "meta": {
        "count": 3
      }
    }
  },
  {
    "transport": "real HTTP",
    "url": "http://127.0.0.1:57548/api/v1/courses",
    "actual_status": 200,
    "actual_body": {
      "data": [
        {
          "classification": null,
          "course_code": null,
          "course_id": "course-demo-001",
          "credits": 3.0,
          "name": "資料結構",
          "offering_department_id": "dept-csie"
        },
        {
          "classification": null,
          "course_code": "DEMO-PROG",
          "course_id": "course-demo-002",
          "credits": 3.0,
          "name": "程式設計",
          "offering_department_id": "dept-csie"
        },
        {
          "classification": null,
          "course_code": "DEMO-MATH",
          "course_id": "course-demo-003",
          "credits": 2.5,
          "name": "離散數學",
          "offering_department_id": "dept-csie"
        },
        {
          "classification": null,
          "course_code": null,
          "course_id": "course-demo-004",
          "credits": 3.0,
          "name": "進階資料分析",
          "offering_department_id": "dept-csie"
        },
        {
          "classification": null,
          "course_code": "DEMO-ANY",
          "course_id": "course-demo-005",
          "credits": 0.0,
          "name": "跨域專題",
          "offering_department_id": "dept-demo"
        },
        {
          "classification": null,
          "course_code": null,
          "course_id": "course-demo-006",
          "credits": 1.0,
          "name": "探索課程",
          "offering_department_id": null
        }
      ],
      "meta": {
        "count": 6
      }
    }
  },
  {
    "transport": "real HTTP",
    "url": "http://127.0.0.1:57548/api/v1/courses/course-demo-001",
    "actual_status": 200,
    "actual_body": {
      "data": {
        "classification": null,
        "course_code": null,
        "course_id": "course-demo-001",
        "credits": 3.0,
        "name": "資料結構",
        "offering_department_id": "dept-csie",
        "prerequisites": {
          "course_ids": null,
          "mode": null,
          "source": null,
          "status": "unknown"
        }
      }
    }
  },
  {
    "transport": "real HTTP",
    "url": "http://127.0.0.1:57548/api/v1/course-offerings?semester_id=semester-115-1",
    "actual_status": 200,
    "actual_body": {
      "data": [
        {
          "class_meetings": [
            {
              "campus_id": "campus-demo",
              "end_time": "10:00",
              "location": "測試教室 A",
              "meeting_id": "meeting-demo-001",
              "start_time": "09:00",
              "weekday": 1
            },
            {
              "campus_id": "campus-demo",
              "end_time": "12:00",
              "location": "測試教室 A",
              "meeting_id": "meeting-demo-002",
              "start_time": "10:00",
              "weekday": 3
            }
          ],
          "course_id": "course-demo-001",
          "course_name": "資料結構",
          "offering_id": "offering-demo-001",
          "schedule_status": "scheduled",
          "section_name": "A班",
          "semester_id": "semester-115-1"
        },
        {
          "class_meetings": [
            {
              "campus_id": null,
              "end_time": "15:00",
              "location": null,
              "meeting_id": "meeting-demo-003",
              "start_time": "13:00",
              "weekday": 2
            }
          ],
          "course_id": "course-demo-001",
          "course_name": "資料結構",
          "offering_id": "offering-demo-002",
          "schedule_status": "scheduled",
          "section_name": "B班",
          "semester_id": "semester-115-1"
        },
        {
          "class_meetings": [],
          "course_id": "course-demo-002",
          "course_name": "程式設計",
          "offering_id": "offering-demo-003",
          "schedule_status": "unknown",
          "section_name": null,
          "semester_id": "semester-115-1"
        },
        {
          "class_meetings": [
            {
              "campus_id": "campus-demo",
              "end_time": "10:00",
              "location": null,
              "meeting_id": "meeting-demo-004",
              "start_time": "09:00",
              "weekday": 4
            },
            {
              "campus_id": "campus-demo",
              "end_time": "15:00",
              "location": "測試教室 B",
              "meeting_id": "meeting-demo-005",
              "start_time": "13:00",
              "weekday": 4
            }
          ],
          "course_id": "course-demo-004",
          "course_name": "進階資料分析",
          "offering_id": "offering-demo-004",
          "schedule_status": "scheduled",
          "section_name": "測試班",
          "semester_id": "semester-115-1"
        }
      ],
      "meta": {
        "count": 4
      }
    }
  }
]
```

## 7. 安裝、初始化、啟動與測試

在專案根目錄執行：

```sh
# 第一次使用才需要安裝；本次沿用既有 .venv，未重新安裝
./scripts/setup-backend.sh

# 新資料庫初始化，或升級既有 /me 資料庫：先停止 server、備份資料庫，再執行
./scripts/init-backend-db.sh

# 預設只監聽 127.0.0.1:5050
./scripts/run-backend.sh
# 如需與原規格的 port 一致：PORT=8000 ./scripts/run-backend.sh
```

Swagger UI：<http://127.0.0.1:5050/docs>。預設資料庫：`backend/instance/profile.sqlite3`。自訂資料庫時，初始化和啟動必須指定相同絕對路徑：

```sh
ME_DATABASE=/absolute/path/catalog.sqlite3 ./scripts/init-backend-db.sh
ME_DATABASE=/absolute/path/catalog.sqlite3 ./scripts/run-backend.sh
```

重跑驗收並另存證據（等號不可省略，避免 pytest 誤判輸出路徑）：

```sh
./scripts/test-backend.sh --evidence=../docs/api/evidence/catalog-results.json
# 只跑新查詢功能：
./scripts/test-backend.sh tests/test_catalog.py --evidence=../docs/api/evidence/catalog-only-results.json
```

測試會使用隔離的暫存 SQLite；真實 HTTP 測試需要允許監聽本機連接埠。JSON 每次自動記錄當次結果，若需要保留歷次證據請使用不同檔名。Markdown 是本次版本快照，後續改碼不代表舊通過結果仍適用。

以下為手動重現指令；**未逐條以 curl 手動執行**，不將它們標為手動測試通過。對應自動驗收結果在第 6 節。

```sh
curl -i 'http://127.0.0.1:5050/api/v1/semesters?academic_year=115'
curl -i -G 'http://127.0.0.1:5050/api/v1/courses' \
  --data-urlencode 'q=資料' --data-urlencode 'rule_set_id=rules-csie-115-v1'
curl -i 'http://127.0.0.1:5050/api/v1/courses/course-demo-001?rule_set_id=rules-csie-115-v1'
curl -i 'http://127.0.0.1:5050/api/v1/course-offerings?semester_id=semester-115-1'
curl -i 'http://127.0.0.1:5050/api/v1/course-offerings'
curl -i 'http://127.0.0.1:5050/api/v1/courses/unknown'
```

依序預期為 200、200、200、200、422、404。預設種子有兩筆 115 學期、兩門課名含「資料」及四筆 115-1 開課，不要求與第 2 節僅一筆的示意回應相同。

## 8. 未完成與未執行項目

| 項目 | 狀態 |
|---|---|
| 正式登入、多使用者隔離 | 未實作／未執行；共用查詢資料無個人選課資訊；既有 /me 的兩項 skip 保持未執行。 |
| 臨時停課、單次調課 | 設計上已知限制／未執行；目前只有每週固定時段。 |
| 個人先修資格判斷、個人修課紀錄 | 未實作／未執行；本 API 僅提供先修規定。 |
| 校方真實資料匯入、AI／導航等外部串接、502 | 不在 baseline 範圍／未執行。 |
| 分頁、效能／壓力測試、多程序競爭 | 未實作或未執行；清單目前全部回傳，採簡單 SQLite 查詢。 |
| 前端串接、Swagger UI 手動點擊、curl 手動重現 | 未執行；OpenAPI 結構與自動真實 HTTP 已另行實測。 |
| 全新環境安裝、開發／正式資料庫實際升級、備份復原 | 未執行；升級僅在暫存舊版資料庫驗證。 |

程式：[API 路由](../../backend/app/catalog.py)、[輸出驗證](../../backend/app/catalog_schemas.py)、[schema 與種子](../../backend/app/catalog_seed.py)、[驗收測試](../../backend/tests/test_catalog.py)。
