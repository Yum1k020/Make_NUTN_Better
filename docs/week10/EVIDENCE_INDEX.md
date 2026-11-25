# Week 10 Evidence Index

Baseline SHA：`1b5124f9ab212f5efefc10dd4997cd65661aae6f`

Verified implementation SHA：`ebc1e604e56d5402c14e7d2a4023159539cf3e1d`

這個 baseline 已包含同學 2026-11-25 的 `fix: align study agent schedule inputs`。

| ID | 證據 | 位置 | 狀態 |
| --- | --- | --- | --- |
| W10-01 | 同學課表來源一致化 | `docs/week10/README.md` | integrated baseline |
| W10-02 | Data Package backend | `backend/app/study_agent_api.py` | PASS |
| W10-03 | Backend timetable citation | `backend/app/study_agent_openai.py` | PASS |
| W10-04 | React Data Package UI | `frontend/src/components/StudyPlanner.jsx` | PASS |
| W10-05 | Backend tests | `backend/tests/test_study_agent_service.py` | 17 passed |
| W10-06 | Frontend contract | `frontend/tests/studyAgentClient.test.js` | 41 / 41 passed |
| W10-07 | Offline acceptance | `week10/run_acceptance.py` | offline_all_pass=true |
| W10-08 | Offline evidence | `week10/evidence/offline_data_package.json` | committed |
| W10-09 | Week 09 regression | GitHub Actions | PASS |
| W10-10 | Week 08 regression | GitHub Actions | PASS |

## GitHub Actions

- Week 10 run：`45530040876`
- Week 10 job：`138922775744`
- Artifact：`14984596003`
- Week 09 regression：`45530040897` → PASS
- Week 08 regression：`45530040946` → PASS

## 驗收重點

- Flask／SQLite timetable source 進入 Environment。
- Flask／SQLite personal events 被計數，但 title / location 被 redacted。
- Week 08 / 09 workflow 形成 7-step observable trajectory。
- deterministic verifier：0 plan issues，assessment expected=actual=balanced。
- credentialsIncluded=false。
- React 能接到並顯示 dataPackage。
