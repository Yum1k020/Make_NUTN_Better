# Week 08 Evidence Index

Baseline SHA：`16c23e237ec091468e03a9461ec740e2ba06e74f`

Verified implementation SHA：`16a0ec65c4027fa13c9f63e20a895de65f7d9b36`。

| ID | 類型 | 證據 | 初始狀態 |
| --- | --- | --- | --- |
| W08-01 | Backend | `backend/app/study_agent_api.py` | implemented |
| W08-02 | Expert provider | `backend/app/study_agent_openai.py` | implemented |
| W08-03 | Backend tests | `backend/tests/test_study_agent_service.py` | PASS |
| W08-04 | Provider permission test | `backend/tests/test_study_agent_openai.py` | PASS |
| W08-05 | Frontend UI | `frontend/src/components/StudyPlanner.jsx` | implemented |
| W08-06 | Frontend contract | `frontend/tests/studyAgentClient.test.js` | PASS |
| W08-07 | Role contract | `docs/week08/ROLE_CONTRACT.md` | documented |
| W08-08 | ADR | `docs/week08/ADR.md` | documented |
| W08-09 | Live | `week08/evidence/LIVE_NOT_RUN.json` | LIVE_NOT_RUN |

## Required observations

正常路徑必須可看到：

```text
Coordinator tool call
-> deterministic tool
-> Expert review
-> Expert return
-> Coordinator final answer
```

邊界至少驗：

- Tool args mismatch → tool 0 calls。
- Expert 收不到私人行程細節。
- Expert 無 tools。
- Expert facts contradiction → final coordinator summary 0 calls。
- Provider／expert failure 有有限停止。

## Security

Evidence 不得含 API key、token、.env、真實私人行程或真實學生資料。


## CI run

- Run：`42939439673`
- Job：`130257464532`
- Backend focused：12 passed
- Frontend：40 / 40 passed
- Production build：PASS
- Prettier：PASS
- Live provider：LIVE_NOT_RUN
