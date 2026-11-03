# 期中版本測試結果

執行日期：2026-11-04（Asia/Taipei）

| 檢查 | 指令 | 結果 |
| --- | --- | --- |
| Python 環境 | `.venv/bin/python scripts/verify_environment.py` | PASS；Python 3.12、Flask、FastAPI、LangGraph、requests 與 SQLite 可用 |
| Python 全套 | `.venv/bin/python -m pytest` | 356 passed、5 skipped、1 xfailed |
| Agentic Weeks 02–07 與 Flask backend | 根目錄 pytest 內含 | PASS；包含 Flask／SQLite、工具 Gate、記憶與 provider contract tests |
| Frontend | `npm test` | 38 passed、0 failed |
| Build | `npm run build` | PASS |
| Format | `npm run format:check` | PASS |
| OpenAI live E2E | 合成資料、Responses API | LIVE_PASS；workflow completed、3 個時段、共 360 分鐘 |
| OpenAI 畢業說明 live | 合成彙整、Responses API | LIVE_PASS；固定規準通過、資料庫未改動 |
| 供應者符合性 | 教師公告指定 Gemini／ADC | 專案目前 OpenAI-only；不應宣稱符合此項要求 |

skip 與 xfail 是測試明示的未執行／已知限制；報告不可把它們寫成通過。OpenAI 主流程的 live 狀態見 `evidence/study-agent-openai-live.json`。
