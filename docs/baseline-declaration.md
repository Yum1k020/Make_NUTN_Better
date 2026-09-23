# Baseline Declaration 初稿

- 案例：學生找一面候選羽球場
- 文件狀態：初稿
- 固定日期：2030-06-17
- 固定時區：Asia/Taipei
- 固定資料：[`fixtures/today-info-2030-06-17.json`](fixtures/today-info-2030-06-17.json)
- 驗收資料：[`fixtures/acceptance-cases.json`](fixtures/acceptance-cases.json)

## 1. User Story

身為想在校內打羽球的學生，我希望輸入日期、開始時間、人數與使用時間後，取得一面符合條件的候選羽球場，以便快速決定可以前往的場地。

## 2. 本次範圍

本次只驗證「推薦一面候選羽球場」：

1. 接收並驗證推薦請求。
2. 讀取固定的合成 `today-info`。
3. 尋找指定日期與時間可用、容量足夠的場地。
4. 最多回傳一面候選球場，或清楚說明無候選結果。

不包含預約、付款、取消、導航、登入、即時校務系統串接、多場地排序與個人化推薦。

## 3. 固定情境與資料

所有驗收都使用 2030-06-17 的合成資料，不查詢真實日期、天氣、課表或場地系統。基準情境如下：

- 學生希望在 2030-06-17 11:00 開始使用 60 分鐘。
- 使用人數為 2 人。
- `court-a` 在 11:00 維護中。
- `court-b` 在 11:00 可使用，容量為 4 人。
- `court-c` 在 11:00 已被占用。
- 正確的唯一候選結果為 `court-b`。

## 4. 輸入協定

### Endpoint

`POST /api/v1/badminton-court-recommendations`

### Request body

| 欄位               | 型別    | 必填 | 驗證規則                              | 基準值       |
| ------------------ | ------- | ---- | ------------------------------------- | ------------ |
| `date`             | string  | 是   | `YYYY-MM-DD`，本次固定為 `2030-06-17` | `2030-06-17` |
| `start_time`       | string  | 是   | 24 小時制 `HH:MM`                     | `11:00`      |
| `duration_minutes` | integer | 是   | 30–120，且為 30 的倍數                | `60`         |
| `party_size`       | integer | 是   | 1–4                                   | `2`          |

最小有效 request：

```json
{
  "date": "2030-06-17",
  "start_time": "11:00",
  "duration_minutes": 60,
  "party_size": 2
}
```

## 5. 輸出協定

### 200：完成推薦

驗收只要求一面候選場地，並能追溯到固定資料中的場地與時段。

```json
{
  "status": "recommended",
  "candidate": {
    "court_id": "court-b",
    "name": "合成羽球場 B",
    "date": "2030-06-17",
    "start_time": "11:00",
    "end_time": "12:00"
  },
  "evidence": {
    "fixture_id": "today-info-2030-06-17",
    "slot_id": "court-b-1100"
  }
}
```

若 request 合法且資料來源正常，但沒有符合條件的場地，仍回傳 `200`，並使用 `{"status":"no_candidate","candidate":null}`。這代表推薦流程已完成，而不是系統錯誤。

### 422：request 不符合協定

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "field": "duration_minutes",
    "message": "duration_minutes 必須是 30 到 120 之間且為 30 的倍數"
  }
}
```

### 502：today-info 無法讀取

```json
{
  "error": {
    "code": "TODAY_INFO_UNAVAILABLE",
    "message": "暫時無法取得 today-info"
  }
}
```

## 6. Baseline 規則

Baseline 採固定、可重現的規則，不呼叫語言模型：

1. `request_validation`：檢查四個 request 欄位；失敗立即回傳 `422`。
2. `today_info_adapter`：載入固定 fixture；逾時或讀取失敗立即回傳 `502`。
3. `candidate_filter`：保留日期與時間吻合、`status` 為 `available`、容量不少於 `party_size`，且可涵蓋完整使用時間的時段。
4. `candidate_selection`：依 `court_id` 穩定排序，取第一面場地；沒有符合項目時回傳 `no_candidate`。
5. `response_contract`：輸出最小可驗證 response。

## 7. 三個驗收案例

三個案例都以「2030-06-17 11:00 找一面候選羽球場」為共同情境；差異只用來固定成功、輸入錯誤與上游錯誤。

| 案例                     | 固定條件                             | 預期 HTTP | 預期停止層           | 不應發生                       |
| ------------------------ | ------------------------------------ | --------- | -------------------- | ------------------------------ |
| `recommendation_success` | 有效 request；today-info 正常        | `200`     | `response_contract`  | 不可回傳多面球場               |
| `invalid_duration`       | `duration_minutes` 固定為 `0`        | `422`     | `request_validation` | 不可讀取 today-info 或執行推薦 |
| `today_info_timeout`     | 有效 request；fixture 模式固定為逾時 | `502`     | `today_info_adapter` | 不可進入候選篩選或捏造場地     |

完整 request 與預期結果保存在 `fixtures/acceptance-cases.json`。

## 8. 11:00 已知失敗紀錄

### 初始 Baseline v0 的行為

初始規則只找到第一筆 `11:00` 時段就停止。fixture 中第一筆是維護中的 `court-a`，因此 Baseline v0 回傳 `no_candidate`，沒有繼續檢查可用的 `court-b`。

### 可重現輸入

```json
{
  "date": "2030-06-17",
  "start_time": "11:00",
  "duration_minutes": 60,
  "party_size": 2
}
```

### 實際與預期

- Baseline v0 實際結果：`200`、`status=no_candidate`、停止在第一筆 11:00 時段。
- 預期結果：`200`、`status=recommended`、`candidate.court_id=court-b`。
- 已知原因：過早停止掃描，未先套用 `status=available` 與容量條件。
- 後續判定：只有回傳 `court-b`，並帶出 `fixture_id` 與 `slot_id`，才算修正此失敗。

## 9. 自我檢核

- [x] 沿用「學生找一面候選羽球場」User Story。
- [x] 範圍只包含推薦，不包含預約。
- [x] 使用 2030-06-17 的合成 today-info。
- [x] 定義最小 request 欄位與可驗證 response。
- [x] 固定 `200`、`422`、`502` 三個案例及停止層。
- [x] 使用固定 fixture 記錄 11:00 的已知失敗。
- [x] 完成 Baseline Declaration 初稿。
- [x] 本版沒有使用跨組交換資料。
