# Week 07 — Agent Memory Architectures

## 本週只做一項記憶增量

原題目仍是「學生個人安排系統」，原 repo 不變。本週選 Route A：保存一個已確認偏好。

固定欄位：

- preference_type = study_session_minutes
- value = 使用者確認的每次複習分鐘數
- owner_id
- source.source_type / source.source_id
- version
- created_at
- expires_at
- superseded_at
- revoked_at

## 缺口

原本智慧排程每次都必須重新提供 session_minutes；換新 session 後，系統沒有一個受控、可更正、可撤回的偏好來源。

## 候選流程

    使用者提出偏好
        ↓
    Gemini / UI 形成 proposal
        ↓
    validator
        ↓
    明確確認
        ├─ NO → 不寫
        ↓ YES
    save_confirmed_preference
        ↓
    memory.json（owner / source / version / expiry）
        ↓ 新 session
    read_preference
        ↓
    preview_with_memory
        ↓
    原 preview_study_plan

偏好只在本次 request 沒有明確 session_minutes 時補上；若 request 已經明確指定分鐘數，當前輸入優先。

## Route A 驗收

- 新 session 可讀回 v1 並接回原排程。
- 跨 user 不可讀。
- 更正建立 v2，之後只讀目前有效版本。
- 撤回後讀不到。
- 未確認不寫。
- 相同 request_id 重送不新增第二筆。
- 過期後不再讀回。
- 非法分鐘數有限停止。

## 程式

- backend/week07_memory.py
- tests/test_week07_memory.py
- week07/run_acceptance.py
- week07/live_memory.py

## 離線執行

    py -m pytest -c pytest_agentic.ini -v
    py -m week07.run_acceptance

## 真實 Gemini

    $env:GEMINI_API_KEY="你的私人 key"
    $env:GEMINI_MODEL="你的可用模型"
    py -m week07.live_memory

只有真實送出本週 Gemini 請求，並完成 proposal → human confirmation → memory write → 新 session read → 原排程 → Gemini summary，才標示 LIVE_PASS。

CI 沒有私人 API key，因此不拿 fixture 冒充 Live。

## 資料範圍

week07/runtime/ 只保存本機合成測試資料，不提交 GitHub。Evidence 不應含 API key、token、ADC JSON 或真實個資。
