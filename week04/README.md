# Week 04 — Tool Use / Function Calling × MCP

本組把「學生個人安排系統」的智慧排程對應成一讀一寫：

- READ：`preview_study_plan`：產生複習排程預覽，不改資料。
- WRITE：`save_study_plan`：只有使用者確認後才寫本機合成資料，並用 request_id 做冪等。

## 安裝
```powershell
py -m pip install -r requirements-agentic-ai.txt
```

## Offline tests
```powershell
py -m pytest -c pytest_agentic.ini -v
```

## MCP 唯讀證據
```powershell
py week04\mcp_check.py
```

會透過 stdio MCP 做 tools/list 與 tools/call，讀取 DATA_GUIDE.md，產生：
`week04/evidence/mcp_read_trace.json`

## 真實 Gemini → tool → Gemini
金鑰不要寫進 repo：

```powershell
$env:GEMINI_API_KEY="你的金鑰"
$env:GEMINI_MODEL="你的帳戶可用模型"
py week04\live_gemini.py
```

沒有成功時不要改成 PASS：
- 沒 key：LIVE_NOT_RUN
- 真實呼叫失敗：LIVE_FAIL
- functionCall → tool → functionResponse → Gemini 摘要成功：LIVE_PASS

## WRITE 人工確認
```powershell
py week04\write_demo.py
```

只有輸入 YES 才會寫入 `week04/runtime/study_sessions.json`。

## 失敗規則
- 必填或日期錯誤：停止，不猜值。
- 時間不足：回 remaining_minutes。
- 未確認：不寫入。
- request_id 重送：不重複寫入。
- Gemini 429 / timeout / 5xx：記錄 provider 失敗，不用假答案補成功。
