# 期中版本測試結果

執行日期：2026-11-03（Asia/Taipei）

| 檢查 | 指令 | 結果 |
| --- | --- | --- |
| Python 環境 | `.venv/bin/python scripts/verify_environment.py` | PASS；Python 3.12、Flask、FastAPI、Google Auth、LangGraph 與 SQLite 可用 |
| Python 全套 | `.venv/bin/python -m pytest` | 356 passed、5 skipped、1 xfailed |
| Agentic Weeks 02–07 與 Flask backend | 根目錄 pytest 內含 | PASS；包含 Flask／SQLite、工具 Gate、記憶與 provider contract tests |
| Frontend | `npm test` | 38 passed、0 failed |
| Build | `npm run build` | PASS |
| Format | `npm run format:check` | PASS |
| OpenAI live E2E | 合成資料、Responses API | LIVE_PASS；HTTP 200、workflow completed、60 分鐘排程 |
| Gemini live E2E | Google Cloud ADC／Vertex AI | LIVE_NOT_RUN；本機未設定 project、model 與 ADC，沒有送出請求 |

5 個 skip 與 1 個 xfail 是既有測試明示的未執行／已知限制；報告不可把它們寫成通過。Gemini 主流程與選用 OpenAI 流程的 live 狀態分別見 `evidence/study-agent-live.json`、`evidence/study-agent-openai-live.json`。
