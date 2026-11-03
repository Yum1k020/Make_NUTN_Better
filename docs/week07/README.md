# Week 07 — Agent Memory Architectures

## 本週只做一項記憶增量

原題目仍是「學生個人安排系統」，原 repo 不變。本週選 Route A：保存一個已確認偏好。

固定欄位：study_session_minutes（使用者確認的每次複習分鐘數），並保存 owner、source、version、expiry、superseded / revoked 狀態。

## 缺口與接法

Baseline SHA：9e2407a9a9a160b5ca5b51fc6e4a090ba077768e

原本智慧排程換新 session 後，session_minutes 必須重新提供。Candidate 在 request 缺少 session_minutes 時，受控讀回目前有效偏好，再接回既有 preview_study_plan；若本輪 request 已明確指定 session_minutes，當前輸入優先。

## Route A 實際驗收

GitHub Actions run：40618188523

Job：122585522782

Implementation SHA：72380961e4d096b8d334d87d53546f750d4292ac

Artifact：12786022642

完整 regression：31 passed, 1 xfailed。

offline_all_pass=true。

已驗證：
- 新 session 讀回 v1=60，原排程仍完成 180 分鐘。
- 跨 user U002 讀 U001 → forbidden。
- 更正 60 → 30 產生 v2，之後只讀 v2。
- 撤回 v2 後 → not_found。
- 未確認 → confirmation_required，0 write。
- 同 request_id 重送 → replayed=true，records 不增加。
- expiry 到期後不再回填。
- 非法分鐘數有限停止。

原本的一項 xfail 是先前保留的 known failure，不是 Week 07 新退步。

## 程式

- backend/week07_memory.py
- tests/test_week07_memory.py
- week07/run_acceptance.py
- week07/live_memory.py
- week07/evidence/offline_comparison.json

## 真實 Gemini

課堂把 LIVE 狀態獨立驗收。GitHub CI 沒有私人 Gemini API key，因此目前仍是 LIVE_NOT_RUN，不用 fixture 冒充。

私有環境執行：

    $env:GEMINI_API_KEY="你的私人 key"
    $env:GEMINI_MODEL="你的可用模型"
    py -m week07.live_memory

只有完成 Gemini proposal → human confirmation → memory write → 新 session read → 原排程 → Gemini summary 才標示 LIVE_PASS。

week07/runtime/ 已 gitignore；不得提交 API key、token、ADC JSON、.env 或真實個資。


---

## 畢業功能線文件（原始分支內容）

# Week 07｜畢業說明的到期與來源更新控制

本組延續「學生個人安排系統」的畢業進度子流程，選 **C 路線：TTL 到期排除**。只對衍生的 AI 說明加上有效範圍，不更動畢業判定、修課採計或既有 Gemini 評估規準。

**繳交與驗收分開：可執行程式、離線證據、比較、ADR 已提交；真實 Gemini 為 LIVE_NOT_RUN，正式跨 user 的 C02 為 NOT_RUN。不能宣稱本週所有驗收通過。**

## 版本與原專題

- Repo：Yum1k020/Make_NUTN_Better。
- 功能分支：`codex/week07-graduation-memory-scope`，預定合併目標 `develop`。
- 由 develop `efca82d4cfb00da9d7c9012fa2fa21d92719214f` 建立本週分支，在本週分支合併 Week 06 `df702d3faddae05dc8eb0831010908ecdc653695`。
- 整合基線：`32ec10231d70448ca43013036eec1f0869a21ce8`，保留 Week 06 程式及 develop 分支規範；沒有改動遠端 develop/main。
- 本週程式版本：`6d97f7e`（完整 SHA 及各檔案雜湊見 evidence）。最後分支 HEAD 另包含繳交文件與測試結果。
- 適用規則仍為後端 mvp-v1；沒有順帶導入目標 v2、GPA、畢業學期預估或新選課演算法。

## 原缺口與本週行為

原版有重新整理時清空說明，但沒有 TTL、定期來源重查或舊非同步結果的世代檢查。實際合成案例：provider 執行期間更新講座資料，原版仍將先前快照標為 verified；候選回傳 stale/SOURCE_CHANGED 並移除說明。不是把原本的清空功能重複算作新增。

- 說明自伺服器讀取來源開始，最多有效 300 秒；重查不延長期限。
- 來源指紋包含畢業進度（排除每次變動的 evaluated_at）及規則文件 digest。指紋在伺服器產生，不把原始修課紀錄送到瀏覽器的重查端點。
- 新說明顯示前重查；Gemini I/O 前後再比對來源。來源更新或生成期間到期，說明不放行。
- 頁面每 15 秒及 focus/visibility 恢復時重查，重查中先隱藏舊說明；失敗即清除。非即時推播：背景變更可能到下一次輪詢才被發現，背景分頁計時器也會被瀏覽器節流。
- 瀏覽器單調時鐘檢查本地剩餘期限，不因電腦牆上時間調整而延長；伺服器時間決定剩餘秒數。
- 新工作階段、導覽離開或重新整理會丟棄頁面記憶；舊請求回來不得復原已清除內容。
- 畢業計算、unknown/null、規劃中不算已得學分、A/B 最多兩稿及 fallback 均保留。

## 資料與清除範圍

| 資料 | 保存位置及範圍 |
|---|---|
| 修課、講座與畢業規則 | 原 SQLite，不因說明清除或到期而刪除 |
| 說明、來源指紋、run ID、期限 | 掛載中的畢業頁記憶；不寫 localStorage 或長期記憶表 |
| 工作階段 scope_id | Flask 簽章的 HttpOnly/SameSite=Strict 瀏覽器 session cookie；沒有成績、姓名或學號 |
| 測試 trace | repo 內僅合成資料；不保存金鑰或模型內部推理 |

新 session 是本功能的說明工作階段，**不是登入身分**。不同 cookie 的 scope 不同，不代表不同學生的資料庫授權已完成。現有固定 user baseline 保留，C02 如實未驗收。到期及清除只停止新使用，不保證抹除截圖、既有回應、瀏覽器開發工具、第三方日誌或備份。

## 修改位置

- `backend/app/graduation_validity.py`：來源指紋、伺服器時鐘、300 秒有效期限。
- `backend/app/graduation_explanation_api.py`：新增 context/reset API，說明 I/O 後重查，no-store。
- `backend/app/__init__.py`：session cookie 與簽章密鑰。
- `frontend/src/lib/graduationMemory.js`：到期、重查、清除、請求世代與導覽後回應處理。
- `frontend/src/components/GraduationProgress.jsx`：期限、提示、輪詢與新工作階段入口。
- 測試與重現：`backend/tests/test_graduation_validity.py`、`frontend/tests/graduationMemory.test.js`、`backend/week07_acceptance.py`。

## 重現方式（PowerShell，repo 根目錄）

沿用 Python 3.12，依既有 backend/requirements-dev.lock.txt 與 requirements-framework.lock.txt 安裝；新功能沒有增加套件。

```powershell
$env:PYTHONUTF8='1'
.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_graduation_validity.py backend/tests/test_graduation_explanations.py --basetemp .cache/pytest-week07-focused --evidence docs/week07/evidence/focused.json
cd frontend
npm ci
npm test
npm run build
cd ..
git worktree add --detach .cache/week07-baseline 32ec10231d70448ca43013036eec1f0869a21ce8
.venv/Scripts/python.exe backend/week07_acceptance.py --compare
.venv/Scripts/python.exe backend/week07_acceptance.py --live
```

`--live` 只讀後端環境變數 GEMINI_API_KEY/GEMINI_MODEL；沒有設定就輸出 LIVE_NOT_RUN，不會改用 fixture 冒充 live。請自行在後端環境設定可用值，不要將金鑰寫入或提交 repo。正常真實 Gemini 仍需符合原 evaluator，通過才記 LIVE_PASS。非法輸入與資料更新案例使用的固定 provider 會另外標為 synthetic/injected。

瀏覽器合成展示（兩個終端）：

```powershell
.venv/Scripts/python.exe backend/week07_acceptance.py --serve-fixture
# 另一個終端
cd frontend
node node_modules/vite/bin/vite.js --config vite.graduation.config.js --host 127.0.0.1
```

開 localhost 顯示的網址，進入畢業進度。**畫面明示合成測試，產生按鈕不連 Gemini。** 正常模式啟動方式沿用 docs/week06/README.md。若多個後端程序共用 cookie，應透過環境變數 GRADUATION_SESSION_SECRET 設定相同的私人值；不設定時使用程序內隨機值，重啟即失去原 scope。這不是正式部署或登入建置。

## 交付索引

- [測試矩陣及未完成項目](TEST_MATRIX.md)
- [原版／候選比較](COMPARISON.md)
- [一頁 Memory ADR](ADR.md)
- [證據索引](EVIDENCE_INDEX.md)

W01/W02 不適用：沒有新增保存偏好、選課或畢業紀錄的寫入工具。session cookie 更新不具有這類業務副作用；其輸入／跨來源拒絕及清除另有實測。

公開證據僅含控制流程、測試結果及內容雜湊；完整合成HTTP/學業payload不發布。請執行已提交的fixture runner重現細節。這是資料省略，不是以摘要冒充真實Gemini或跨user通過。
