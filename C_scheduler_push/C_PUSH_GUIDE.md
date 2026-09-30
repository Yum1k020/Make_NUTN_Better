# C 智慧排程：這次要推的檔案

這包只包含 C 負責的排程模組與測試，不會覆蓋同學目前的 README、DATA_GUIDE、前端或畢業規則。

## 要放進 repo 的檔案

```text
backend/
├─ __init__.py
└─ scheduler.py

tests/
├─ fixtures/
│  ├─ scheduler_success.json
│  └─ scheduler_insufficient.json
└─ test_scheduler.py

pytest.ini
```

## 排程模組介面

```python
from backend.scheduler import build_study_plan

result = build_study_plan(
    plan_id="plan-001",
    start_date="2026-10-01",
    exam_date="2026-10-03",
    target_minutes=180,
    session_minutes=60,
    allowed_windows=[
        {"date": "2026-10-01", "start_time": "09:00", "end_time": "13:00"}
    ],
    busy_intervals=[
        {
            "source_type": "class",
            "source_id": "class-001",
            "title": "作業系統",
            "starts_at": "2026-10-01T10:00:00",
            "ends_at": "2026-10-01T11:00:00"
        }
    ],
)
```

回傳：

```json
{
  "plan_id": "plan-001",
  "suggested_sessions": [],
  "scheduled_minutes": 180,
  "remaining_minutes": 0,
  "reason": "scheduled_in_available_windows"
}
```

## 本版規則

- 使用分鐘，不使用小時。
- `session_minutes` 決定每次複習區塊長度。
- 避開所有 `busy_intervals`。
- 時間區間採半開區間 `[start, end)`：
  - 09:00–10:00 的課
  - 10:00 開始讀書
  - 不算衝突。
- `exam_date` 目前依第一版資料契約，排程只排到考試前一天。
- 空閒時間不足時，不硬塞；回傳 `remaining_minutes`。
- 本模組不直接寫資料庫，也不直接改前端。
- B 的 API 之後只需要呼叫 `build_study_plan(...)`。

## 測試

在 repo 根目錄：

```powershell
py -m pip install pytest
py -m pytest -v
```

預期：

```text
4 passed
```

## Git 推送

先確認自己在 C 的分支：

```powershell
git checkout -b feature/scheduler
```

把這包內的 `backend/`、`tests/`、`pytest.ini` 複製到 repo 根目錄後：

```powershell
git status
py -m pytest -v
git add backend tests pytest.ini
git commit -m "feat: add study scheduling module"
git push -u origin feature/scheduler
```

然後在 GitHub 建 Pull Request：

```text
feature/scheduler -> main
```

## 與 B 串接時

B 的 FastAPI endpoint 可以：

```python
from backend.scheduler import build_study_plan

result = build_study_plan(
    plan_id=request.plan_id,
    start_date=request.start_date,
    exam_date=request.exam_date,
    target_minutes=request.target_minutes,
    session_minutes=request.session_minutes,
    allowed_windows=request.allowed_windows,
    busy_intervals=request.busy_intervals,
)
```

C 不需要直接修改 B 的 API 檔案。
