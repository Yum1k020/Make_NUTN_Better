# 校園日程前端原型

以 React 與 Vite 製作的學生個人安排系統前端，供團隊檢查畫面與操作流程。使用者可在桌面與手機查看週課表、待辦、私人行程、複習建議、修課規劃及畢業進度。

## 啟動

需 Node.js 22 以上版本。

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
- 修課規劃：加入或移除下學期課程，檢視先修提醒與規劃學分。
- 畢業進度：顯示測試規則中的已取得學分、必修與講座缺項；規劃中的課程不計入已取得學分。
- 資料證據：整理 Week 03 gate 的 proposal、source cards、3 個 fixed queries、top-k trace、generator comparison JSON 與 failure observation；目前使用學生系統 fixture 驗證，不把羽球場 baseline 範例當成產品需求。
- 校區地圖：府城校區總覽、府城教室配置與榮譽教學中心配置；點選課表中的課程地點可開啟對應地圖，並能縮放及查看原圖。

## OpenAI Agents SDK 接口

OpenAI API key 只由本機伺服器讀取，不在畫面輸入，也不會經由 Vite 的 `VITE_*` 變數提供給瀏覽器。請在專案根目錄複製 `.env.example` 成 `.env.local`，只在 `.env.local` 填入自己的 key；該檔已被 `.gitignore` 排除，不要提交。

```bash
cd ..
cp .env.example .env.local
```

```env
OPENAI_API_KEY=你的 OpenAI API key
OPENAI_MODEL=gpt-5-mini
OPENAI_AGENTS_TRACING=false
```

主要程式碼入口：

- `server/studyAgent.js`：建立單一 Agent、`get_validated_study_plan` function tool 與 structured output。
- `server/studyAgentMiddleware.js`：提供同源 `/api/study-agent/run` API，並只在伺服器端讀取金鑰。
- `src/lib/studyAgentClient.js`：前端送出規劃資料，不包含 API key。
- `src/lib/planner.js`：保留原本可重複驗證的排程與衝突規則，是時段結果的唯一依據。

進入「智慧學習」按下「用 Agent 產生學習計畫」後，畫面會先保留原規則產生的排程，再請 Agent 呼叫規則工具並回傳說明。若框架結果與原規則不一致或 API 暫時失敗，前端不採用框架排程。若新增或修改 `.env.local`，請重新啟動 `npm run dev`。

## Week 06 Prompt Chaining

「智慧學習」的 Agent 入口現在會依序執行「需求驗證 → 規則排程 → 衝突與完整性 Gate → Agent 說明」。前一階段失敗時不會執行後續階段；畫面會顯示階段狀態、外部證據計數、stop reason 與 run ID，但不顯示個人行程內容或模型內部推理。

程式位於 `server/studyPlanWorkflow.js`，四條必備案例位於 `tests/studyPlanWorkflow.test.js`；完整比較、ADR 與證據索引請見 [`../docs/week06/README.md`](../docs/week06/README.md)。

完成一般測試後，可執行一次需要網路及少量 API 用量的實際 smoke test。這個測試只送出合成課名、日期與空的私人行程，不會讀取畫面中的使用者資料：

```bash
cd frontend
npm run agent:smoke
```

替換理由、驗收案例與限制記錄於 [`../docs/week04-framework-replacement.md`](../docs/week04-framework-replacement.md)。

目前使用固定示範日期 **2026-09-17** 和本機示範資料。使用者的待辦、私人行程、複習建議與修課規劃會保存在瀏覽器 `localStorage`。尚未連接登入、學校課務系統或正式後端代理。地圖圖片由使用者提供；教室與畢業條件仍以實際校方資料為準。
