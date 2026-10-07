# 校園日程前端原型

以 React 與 Vite 製作的學生個人安排系統前端，供團隊檢查畫面與操作流程。使用者可在桌面與手機查看週課表、待辦、私人行程、複習建議、修課規劃及畢業進度。

## 啟動

需 Node.js 20.19 以上版本。

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

## OpenAI 程式碼接口

OpenAI API key 以程式碼設定讀取，不在畫面輸入。請複製 `.env.example` 成 `.env.local`，並只在 `.env.local` 填入自己的 key；`.env.local` 已被 `.gitignore` 排除，不要提交。

```bash
cp .env.example .env.local
```

```env
VITE_OPENAI_API_KEY=你的 OpenAI API key
VITE_OPENAI_MODEL=gpt-5-mini
```

程式碼入口在 `src/lib/openaiAgent.js`：

- `getOpenAIConfig()`：讀取 `VITE_OPENAI_API_KEY`、`VITE_OPENAI_MODEL` 與 Responses API endpoint。
- `buildOpenAIRequest()`：把 Week 03 evidence gate 的 selected evidence 組成 OpenAI request body。
- `generateEvidenceLockedAnswer()`：用設定好的 API key 呼叫 OpenAI Responses API。

資料證據頁的 `Generator comparison` 區塊已接上 `generateEvidenceLockedAnswer()`；按下「OpenAI 產生」會用 selected evidence 產生 live 回答。若新增或修改 `.env.local`，請重新啟動 `npm run dev`，Vite 才會重新載入環境變數。

目前使用固定示範日期 **2026-09-17** 和本機示範資料。使用者的待辦、私人行程、複習建議與修課規劃會保存在瀏覽器 `localStorage`。尚未連接登入、學校課務系統或正式後端代理。地圖圖片由使用者提供；教室與畢業條件仍以實際校方資料為準。
