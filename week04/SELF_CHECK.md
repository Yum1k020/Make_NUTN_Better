# Week 04 Self Check

> 實際執行後更新。OFFLINE 不可寫成 LIVE。

| 項目 | 狀態 | 證據 |
|---|---|---|
| READ 不修改資料 | PASS（offline） | tests/test_week04_tools.py |
| WRITE 未確認不執行 | PASS（offline） | tests/test_week04_tools.py |
| WRITE 確認後寫入 | PASS（offline） | tests/test_week04_tools.py |
| request_id replay 不重複寫入 | PASS（offline） | tests/test_week04_tools.py |
| 時間不足回 remaining_minutes | PASS（offline） | tests/test_week04_tools.py |
| MCP tools/list + tools/call 唯讀 | 未測 | 跑 py week04\mcp_check.py |
| 真實 Gemini functionCall | LIVE_NOT_RUN | 跑 py week04\live_gemini.py |
| functionResponse 後 Gemini 摘要 | LIVE_NOT_RUN | week04/evidence/LIVE-*.json |
| 人工確認後才 WRITE | 未測 | 跑 py week04\write_demo.py |
| 可重現失敗 | PASS（offline） | 未確認 WRITE 被阻止 |

## Version
- Repo URL：https://github.com/Yum1k020/Make_NUTN_Better
- Commit SHA：PR 建立後填
- Run ID：實測後填
- Gemini model：實測後填
- MCP protocol：實測後填

## Known issues
- WRITE 目前只寫本機合成 JSON，尚未串正式資料庫。
- 尚未接正式前端 UI。
- 真實 Gemini / MCP 證據必須本機執行後更新，不可用 mock 代替。
