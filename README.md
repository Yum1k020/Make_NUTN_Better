from datetime import datetime, time, timedelta
from typing import List

from .models import StudyPlanRequest, StudyBlock


DAY_START = time(9, 0)
DAY_END = time(22, 0)
BLOCK_HOURS = 1


def _overlaps(start: datetime, end: datetime, busy_start: datetime, busy_end: datetime) -> bool:
    return start < busy_end and end > busy_start


def build_study_plan(request: StudyPlanRequest) -> tuple[List[StudyBlock], float, float]:
    required = float(request.exam.required_study_hours)
    remaining = required
    result: List[StudyBlock] = []

    current_date = request.available_range.start
    end_date = request.available_range.end

    while current_date <= end_date and remaining > 0:
        cursor = datetime.combine(current_date, DAY_START)
        day_end = datetime.combine(current_date, DAY_END)

        while cursor < day_end and remaining > 0:
            duration = min(BLOCK_HOURS, remaining)
            candidate_end = cursor + timedelta(hours=duration)

            if candidate_end > day_end:
                break

            # 不允許排到考試時間之後
            if cursor >= request.exam.exam_date:
                break

            has_conflict = any(
                _overlaps(cursor, candidate_end, busy.start, busy.end)
                for busy in request.busy_intervals
            )

            if not has_conflict:
                result.append(StudyBlock(start=cursor, end=candidate_end))
                remaining -= duration

            cursor += timedelta(hours=BLOCK_HOURS)

        current_date += timedelta(days=1)

    scheduled = required - remaining
    return result, round(scheduled, 2), round(remaining, 2)
