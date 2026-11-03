import json
import uuid
from pathlib import Path

from backend.week04_tools import preview_study_plan, save_study_plan

ROOT = Path(__file__).resolve().parents[1]
fixture = ROOT / "tests" / "fixtures" / "week04_plan.json"
store = ROOT / "week04" / "runtime" / "study_sessions.json"

request_data = json.loads(fixture.read_text(encoding="utf-8"))
preview = preview_study_plan(**request_data)
print(json.dumps(preview, ensure_ascii=False, indent=2))

answer = input("\n確認寫入本機合成資料？只有輸入 YES 才執行：").strip()
confirmed = answer == "YES"
request_id = f"REQ-{uuid.uuid4().hex[:12].upper()}"

result = save_study_plan(
    preview=preview,
    confirmed=confirmed,
    request_id=request_id,
    store_path=store,
)
print(json.dumps(result, ensure_ascii=False, indent=2))
