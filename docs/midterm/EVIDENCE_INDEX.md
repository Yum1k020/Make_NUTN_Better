# 期中證據索引

課堂報告基線：`fa740a8563eaf0f0b55853d6e9542b88d6fb2545`；選用 OpenAI 後端擴充版本：`ea6798f4d081d50c8c61f1ca13a8ba1609ff274b`（2026-11-03）。

| ID | 類型 | 案例 | 證據 | 目前狀態 |
| --- | --- | --- | --- | --- |
| M01 | 正常 | Python 完整回歸 | `python -m pytest` | 345 passed、5 skipped、1 xfailed |
| M02 | 正常 | 前端互動單元測試 | `frontend` 的 `npm test` | 39/39 passed |
| M03 | 正常 | Production build | `frontend` 的 `npm run build` | PASS |
| M04 | 正常 | 格式檢查 | `frontend` 的 `npm run format:check` | PASS |
| M05 | 主流程 | Gemini ADC function calling | `evidence/study-agent-live.json` | LIVE_NOT_RUN；project 與 model 未設定，未送出請求 |
| M06 | 邊界 | 模型工具參數改寫 | `backend/tests/test_study_agent_vertex.py` | PASS，工具 0 次 |
| M07 | 邊界 | 非法輸入 | `backend/tests/test_study_agent_vertex.py` | PASS，HTTP 422 |
| M08 | 寫入 | 未確認與重送 | `tests/test_week04_tools.py`、`tests/test_week05_langgraph.py` | PASS |
| M09 | 記憶 | 更正、撤回、到期、跨 user、冪等 | `tests/test_week07_memory.py`、`frontend/tests/studyMemory.test.js` | PASS |
| M10 | 畢業說明 | 來源更新、TTL、舊回應 | `backend/tests/test_graduation_validity.py`、`frontend/tests/graduationMemory.test.js` | PASS_OFFLINE |
| M11 | 報告 | 14 頁 PDF 與可編輯 PPTX | `reports/midterm/` | PPTX package／layout 驗證通過；PDF 逐頁渲染檢查通過 |
| M12 | 選用流程 | OpenAI Responses API function calling | `evidence/study-agent-openai-live.json` | LIVE_PASS；HTTP 200、workflow completed、60 分鐘排程 |

## Live 狀態定義

- `LIVE_NOT_RUN`：未實際送出本版本指定供應者的請求。
- `LIVE_FAIL`：實際送出，但因權限、配額、網路、模型或輸出驗證失敗。
- `LIVE_PASS`：本版本完成 function call、工具參數驗證、工具執行、function output 與結構化摘要。

M12 證明選用 OpenAI 後端介面可運作，但不能取代課程要求的 M05 Gemini／ADC 主流程證據。

## 報告前需要補的證據

1. 在已設定 ADC 的後端執行 `python backend/midterm_live.py`。
2. 檢查 JSON 為 `LIVE_PASS`，再錄製完整 UI 流程與失敗 fallback。
3. 截圖須包含執行日期 2026-11-03 或 2026-11-04、commit SHA、live 狀態與 run ID。
4. 不得把 ADC JSON、token、console credential 或真實學生資料錄入畫面。
