# 期中版本測試結果

執行日期：2026-11-03（Asia/Taipei）

| 檢查 | 指令 | 結果 |
| --- | --- | --- |
| Python 全套 | `../.venv/bin/python -m pytest` | 341 passed、5 skipped、1 xfailed；3 個真實 HTTP 測試需允許本機 loopback |
| Agentic Weeks 02–07 | 根目錄 pytest 內含 | 31 passed、1 xfailed |
| Flask backend | 根目錄 pytest 內含 | 310 passed、5 skipped（包含新增 6 個 Gemini／ADC contract tests） |
| Frontend | `npm test` | 39 passed、0 failed |
| Build | `npm run build` | PASS |
| Format | `npm run format:check` | PASS |

5 個 skip 與 1 個 xfail 是既有測試明示的未執行／已知限制；報告不可把它們寫成通過。完整 live 狀態另見 `evidence/study-agent-live.json`。
