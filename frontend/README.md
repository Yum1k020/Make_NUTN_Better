# 校園日程前端原型

以 React 與 Vite 製作的學生個人安排系統前端，供團隊檢查畫面與操作流程。使用者可在桌面與手機查看週課表、待辦、私人行程、複習建議、修課規劃及畢業進度。

## 啟動

需 Node.js 22 以上版本。

主示範的 Agent API 位於 Flask 後端；先從 repository 根目錄啟動後端：

```bash
./scripts/init-backend-db.sh
./scripts/run-backend.sh
```

另一個終端啟動前端：

```bash
cd frontend
npm install
npm run dev
```

瀏覽器開啟終端機顯示的本機網址。建置與排程測試：

```bash
npm run build
npm test
npm run format:check
```

## 目前可操作的功能

- 今日／本週：週課表與單日時間軸切換、日期切換、待辦完成狀態、新增／編輯／刪除待辦與私人行程。
- 私人行程與既有課程或其他私人行程時間重疊時，表單會提示衝突並要求調整。
- 智慧學習：先預覽本週課程與個人行程，再設定考試日期、複習時數和可安排時段，計算不與課程和行程重疊的複習建議；時段不足會顯示缺少時數，亦可手動調整或移除建議。
- 學習偏好記憶：使用者可明確確認一個每次複習分鐘數；新 session 會讀回並預選，可更正、到期與撤回。本次手動選擇的時長不會自動保存。
- 修課規劃：加入或移除下學期課程，檢視先修提醒與規劃學分。
- 畢業進度：顯示測試規則中的已取得學分、必修與講座缺項；規劃中的課程不計入已取得學分。
- 資料證據：整理 Week 03 gate 的 proposal、source cards、3 個 fixed queries、top-k trace、generator comparison JSON 與 failure observation；目前使用學生系統 fixture 驗證，不把羽球場 baseline 範例當成產品需求。
- 校區地圖：府城校區總覽、府城教室配置與榮譽教學中心配置；點選課表中的課程地點可開啟對應地圖，並能縮放及查看原圖。

## Google Cloud／ADC Gemini 主流程

前端只呼叫同源 `/api/v1/study-agent/run`，不保存 Google 憑證、access token 或模型 key。Flask 後端使用 Google Cloud Application Default Credentials 呼叫 Vertex AI Gemini。

本機開發需在私有環境設定 ADC 與非敏感設定：

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="你的 Google Cloud project ID"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_CLOUD_GEMINI_MODEL="gemini-2.5-flash"
```

不得把 ADC JSON、token 或 `.env` 提交到 Git。主流程：

```text
前端需求
  -> Flask schema 驗證
  -> Gemini function call
  -> 工具參數與原需求一致性檢查
  -> get_validated_study_plan
  -> functionResponse 回送 Gemini
  -> 結構化說明與前端規則結果比對
```

主要程式碼入口：

- `../backend/app/study_agent_api.py`：後端輸入驗證、確定性工具、Gate 與 HTTP API。
- `../backend/app/study_agent_vertex.py`：ADC、Vertex AI REST function calling 與 `functionResponse`。
- `src/lib/studyAgentClient.js`：前端只送規劃資料，不包含憑證。
- `src/lib/planner.js`：前端保留相同規則結果，作為 UI fallback 與結果一致性檢查。

進入「智慧學習」按下「用 Agent 產生學習計畫」後，畫面會先保留規則排程，再顯示 Gemini 工具流程。若 ADC、權限、網路或模型失敗，前端不採用未驗證的模型結果。

`server/studyAgent.js` 與 `server/studyAgentMiddleware.js` 保留為 Week 04 的歷史 OpenAI Agents SDK 比較實作，但不再是主網站的預設路徑。

## Week 06 Prompt Chaining

「智慧學習」的 Agent 入口現在會依序執行「需求驗證 → 規則排程 → 衝突與完整性 Gate → Agent 說明」。前一階段失敗時不會執行後續階段；畫面會顯示階段狀態、外部證據計數、stop reason 與 run ID，但不顯示個人行程內容或模型內部推理。

程式位於 `server/studyPlanWorkflow.js`，四條必備案例位於 `tests/studyPlanWorkflow.test.js`；完整比較、ADR 與證據索引請見 [`../docs/week06/README.md`](../docs/week06/README.md)。

完成一般測試後，可執行一次需要網路及少量 API 用量的實際 smoke test。這個測試只送出合成課名、日期與空的私人行程，不會讀取畫面中的使用者資料：

```bash
cd frontend
npm run agent:smoke
```

替換理由、驗收案例與限制記錄於 [`../docs/week04-framework-replacement.md`](../docs/week04-framework-replacement.md)。

## Week 07 已確認偏好記憶

「智慧學習」會透過同源 `/api/study-memory/preference` API 讀寫一筆 `study_session_minutes`。只有按下「確認並保存」才會寫入；記憶包含 owner、來源、版本與 30 天期限，撤回或到期後不再回填。記憶只預選 UI 的每次安排時長，原排程仍重新檢查課表、私人行程與本次輸入。

預設資料檔是 `data/study-memory.json`，已由專案根目錄 `.gitignore` 排除。這是本機課堂原型，示範 user header 不是正式登入驗證；不要在該檔放入真實個資。實作、測試矩陣、比較表與 ADR 請見 [`../docs/week07/README.md`](../docs/week07/README.md)。

目前使用固定示範日期 **2026-09-17** 和本機示範資料。使用者的待辦、私人行程、複習建議與修課規劃會保存在瀏覽器 `localStorage`。尚未連接登入、學校課務系統或正式後端代理。地圖圖片由使用者提供；教室與畢業條件仍以實際校方資料為準。
