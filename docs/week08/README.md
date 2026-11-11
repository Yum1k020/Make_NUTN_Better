# Week 08 — Multi-Agent Systems：智慧學習受限專家

## 一句話交付

延續原「學生個人安排系統」與原「智慧學習」入口，本週選 **Route A｜一位受限專家**。

Baseline：`16c23e237ec091468e03a9461ec740e2ba06e74f`（`codex/backend-persistence`）。

原本單一 Study Agent 仍保留主控制權；在確定性排程完成後，新增一個 **Study Load Review Expert**。專家只拿到去識別的讀書時段封包、沒有 Tool、沒有資料庫寫入權限，回報後由原 Coordinator 整合最後回答。

## 原入口與前後端

使用者仍在 React「智慧學習」按 **用 Agent 產生學習計畫**。

```text
React StudyPlanner
  -> POST /api/v1/study-agent/run
  -> Flask request validation
  -> Study Coordinator
  -> get_validated_study_plan
  -> deterministic planner / Gate
  -> Study Load Review Expert
  -> expert return packet
  -> Study Coordinator final summary
  -> Flask JSON response
  -> React Multi-Agent trace + schedule
```

Vite 仍用 `/api/v1 -> http://127.0.0.1:5050` proxy；沒有新增第二套前端或平行 API。

## 為什麼選 Route A

目前智慧排程的時間計算、衝突與寫入安全都已經有強的單一基線。這週不需要把整個網站拆成多 Agent。

新增專家的目的很小而明確：在原排程工具完成後，獨立檢查「是否仍缺時數、讀書時段是否過度集中」，再把建議交回原 Coordinator。這個角色不重新計算排程，也不能改資料。

## 角色

### Study Coordinator

- Owner：主流程與最後回答。
- Context：完整已驗證 request、tool result、專家回報。
- Tool：`get_validated_study_plan`。
- 權限：唯讀排程工具；寫入仍走原有 UI／Flask 明確操作，不由本週 MAS 自動執行。
- 最後回答：是。

### Study Load Review Expert

- 責任：檢查讀書負荷、剩餘分鐘與時段集中程度。
- Context：只拿 courseName、日期範圍、總時數、單次時長、allowedPeriods、去識別 sessions、remainingMinutes。
- Tool：**無**。
- DB write：**無**。
- 不共享：私人行程標題、地點、完整 Memory、API key。
- 回傳：assessment、summary、最多三項 recommendations、citations。
- 最後回答：否，結果回 Coordinator。

## 控制語意

這是 **Agent-as-tool / bounded specialist**，不是 Handoff。

Coordinator 始終保留主控制權；專家完成限定子任務後把結果交回 Coordinator。UI 會顯示：

```text
Study Coordinator
  -> Study Load Review Expert
  -> Study Coordinator
```

若專家輸出與 deterministic facts 矛盾，例如已排滿卻回 `insufficient`，後端拒絕該輸出並停止後續 Coordinator summary。

## 前端可觀察證據

「智慧學習」Agent 區塊新增：

- `2-Agent Route A` 標記。
- Coordinator 與 Study Load Review Expert 兩個角色。
- 專家沒有 Tool／DB write 權限。
- 專家 assessment、summary、recommendations。
- Workflow stages：
  - validate-request
  - model-tool-call
  - validate-tool-args
  - execute-tool
  - delegate-study-load-expert
  - integrate-expert-review
  - return-tool-result

## 測試

Backend：

```bash
python -m pytest backend/tests/test_study_agent_service.py backend/tests/test_study_agent_openai.py -q
```

重點案例：

1. 正常路徑真的出現兩角色並回傳 `multiAgent`。
2. 專家封包不含 `personalEvents`、私人行程標題或地點。
3. 專家沒有 Tool 權限；OpenAI expert request 不送 `tools`。
4. 專家輸出若和 deterministic facts 矛盾，停止為 `EXPERT_OUTPUT_INVALID`。
5. 原 `TOOL_ARGUMENT_MISMATCH` 仍在工具執行前停止。

Frontend：

```bash
cd frontend
npm test
npm run build
npm run format:check
```

`frontend/tests/studyAgentClient.test.js` 驗證 `multiAgent` 從 Flask API 回到前端契約且不破壞 deterministic plan comparison。

## Live 狀態

本週新增了一次額外模型呼叫（受限專家），所以不能沿用 Week 07／期中的舊 Live 證據。

目前 GitHub CI 沒有私人 `OPENAI_API_KEY`，因此 Week 08 真實 provider 狀態先維持 **LIVE_NOT_RUN**。只有本版本完成 Coordinator → Tool → Expert → Coordinator 才可改為 LIVE_PASS。

## 啟動

後端：

```bash
./scripts/init-backend-db.sh
./scripts/run-backend.sh
```

前端：

```bash
cd frontend
npm install
npm run dev
```

瀏覽器開啟 Vite 顯示的網址，進入「智慧學習」。

## 交付索引

- 實作：`backend/app/study_agent_api.py`
- Provider：`backend/app/study_agent_openai.py`
- Backend tests：`backend/tests/test_study_agent_service.py`、`backend/tests/test_study_agent_openai.py`
- Frontend：`frontend/src/components/StudyPlanner.jsx`
- Frontend contract test：`frontend/tests/studyAgentClient.test.js`
- Role contract：`docs/week08/ROLE_CONTRACT.md`
- ADR：`docs/week08/ADR.md`
- Evidence index：`docs/week08/EVIDENCE_INDEX.md`
- Live placeholder：`week08/evidence/LIVE_NOT_RUN.json`


## GitHub Actions 實測

Verified implementation SHA：`4205678a89b684eefa7cddf56f8fe2af68360831`

- Run ID：`42939717922`
- Job ID：`130258360188`
- Backend focused：12 tests passed（`test_study_agent_service.py` + `test_study_agent_openai.py`）
- Frontend：40 / 40 passed
- Vite production build：PASS
- Prettier：PASS

這組 CI 驗證的是 Week 08 垂直切片與完整 frontend test suite；不宣稱本次重新執行整個 repository 的所有 Python 測試。
