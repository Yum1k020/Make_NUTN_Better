# Week 05 — Frameworks & Orchestration

## 本週選的替換邊界

只替換「複習排程預覽完成後，等待使用者確認，再接續寫入」這一段流程。

原版位置：

- week04/write_demo.py：手動呼叫 preview，讀取 YES，再呼叫 save。
- backend/week04_tools.py：保留排程與寫入業務規則。

候選位置：

- backend/week05_langgraph.py
- LangGraph StateGraph + interrupt + Command(resume=...) + SQLite checkpoint

這不是把整個學生系統改成 LangGraph，也沒有把 scheduler、精確確認、request_id 冪等或實際 JSON 寫入規則交給框架。

## 保留／替換／轉接

| 類型 | 內容 |
|---|---|
| 替換 | 等待人工確認、同 thread 接續、checkpoint |
| 保留 | preview_study_plan、save_study_plan、scheduler_v1、只接受精確 YES、request_id 冪等 |
| 轉接 | Week 04 preview/result dict ↔ LangGraph State；thread_id ↔ checkpoint |

## 固定驗收條件

沿用 tests/fixtures/week04_plan.json，不換資料、不換排程規則。

1. 候選 preview 必須和 Week 04 原版完全相同。
2. interrupt 暫停時不得建立 study session。
3. 拒絕不得寫入。
4. 關閉 runtime 後，以相同 thread_id 重新建立 runtime，仍可用 YES 接續並寫入。
5. 同 request_id 在新 thread 重送，不得新增第二批 session。
6. 小寫 yes 仍視為未精確確認，不得寫入。

## 安裝與測試

    py -m pip install -r requirements-agentic-ai.txt
    py -m pytest -c pytest_agentic.ini -v
    py -m week05.run_acceptance

run_acceptance 會產生：

    week05/evidence/week05_comparison.json

## 人工示範：真的分成兩個程序

第一個程序：

    py -m week05.run_demo start

看到 awaiting_confirmation 後，程式已經結束；此時尚未寫入。

第二個程序：

    py -m week05.run_demo resume YES

它會從 week05/runtime/langgraph.sqlite 讀回同一 thread 的 checkpoint，再執行原本的 save_study_plan。

week05/runtime/ 已忽略，不會把 SQLite 狀態或本機合成寫入資料推到 GitHub。

## 模型與 API

這次替換的是「人工確認與流程接續」，不是模型工具迴圈，所以 Week 05 驗收本身需要 0 次 Gemini 呼叫，也不需要 API key。Week 04 的 Gemini LIVE_FAIL 證據仍維持原狀，不拿歷史回放冒充本週 Live。

## 回退方式

候選沒有覆蓋 Week 04 原版。若 LangGraph 相依或 checkpoint 行為不符合需求，直接回到 week04/write_demo.py 與 backend/week04_tools.py 即可。
