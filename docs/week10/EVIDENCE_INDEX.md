# Week 10 Evidence Index

Baseline SHA：`1b5124f9ab212f5efefc10dd4997cd65661aae6f`

這個 baseline 已包含同學 2026-11-25 的 `fix: align study agent schedule inputs`。

| ID | 證據 | 位置 | 狀態 |
| --- | --- | --- | --- |
| W10-01 | 同學課表來源一致化 | `docs/week10/README.md` | baseline |
| W10-02 | Data Package backend | `backend/app/study_agent_api.py` | implemented |
| W10-03 | Backend timetable citation | `backend/app/study_agent_openai.py` | implemented |
| W10-04 | React Data Package UI | `frontend/src/components/StudyPlanner.jsx` | implemented |
| W10-05 | Backend tests | `backend/tests/test_study_agent_service.py` | CI pending |
| W10-06 | Frontend contract | `frontend/tests/studyAgentClient.test.js` | CI pending |
| W10-07 | Offline acceptance | `week10/run_acceptance.py` | CI pending |
| W10-08 | Offline evidence | `week10/evidence/offline_data_package.json` | CI generated |

## 驗收重點

- Flask／SQLite timetable source 進入 Environment。
- Flask／SQLite personal events 被計數，但 title / location 被 redacted。
- Week 08 / 09 workflow 形成可觀察 trajectory。
- deterministic verifier 必須 PASS。
- credentialsIncluded=false。
- React 能接到並顯示 dataPackage。
