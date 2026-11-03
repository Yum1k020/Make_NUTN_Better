# Make_NUTN_Better

組員：蔣仲鋰、張華庭、陳苾妏、呂安婷

## 分支與合併流程

- `main`：保留完成整合與驗證的穩定版本。
- `develop`：開發整合分支，後續功能與修正先合併到這裡。
- 新功能或修正從最新的 `develop` 建立功能分支，完成後以 `develop` 為合併目標。
- 整體功能完成、測試與驗收通過後，再將 `develop` 合併回 `main`。

合併方向：`功能分支 → develop → main`。

透過 AI Agent 改善大學生的校園生活。本專案最終選定「學生個人安排系統」，整合課表、待辦事項、私人行程、學習規劃與畢業進度，協助學生安排時間並掌握修課需求。

## 學生個人安排系統

將先前提案中的「課表與學習規劃」及「學分與畢業進度追蹤」整合為同一個系統，同時處理學生的日常安排與長期修課規劃。

- **Problem：** 學生的課表、作業、考試與私人行程分散在不同地方，難以統一安排時間；規劃選課時，也需要自行比對學分與畢業條件，容易遺漏待辦事項、延誤複習或漏修必要課程。
- **Target user：** 需要整合日常行程、學習規劃與畢業進度的大學生。
- **User Story：** 身為大學生，我希望在同一個系統查看課表、管理待辦與行程，依空閒時間安排複習，並追蹤已取得的學分、尚缺的必修課與講座，以便兼顧日常生活與課業，並如期畢業。

### 核心功能

| 功能           | 說明                                                                     |
| -------------- | ------------------------------------------------------------------------ |
| 課表整合       | 統一顯示課程名稱、上課時間與地點。                                       |
| 待辦與行程管理 | 管理作業期限、考試日期、私人行程與完成狀態。                             |
| 學習規劃       | 依照可用時間、考試日期及所需複習時數安排讀書進度。                       |
| 衝突提醒       | 提醒使用者行程重疊或可用複習時間不足。                                   |
| 畢業進度追蹤   | 比對修課紀錄與適用的畢業規則，顯示已取得學分及尚缺的必修課、講座等條件。 |

### AI Agent 的用途

目前有兩條受限 Agent 子流程：

1. **智慧學習主示範：** 前端將需求送到 Flask 後端；後端先驗證 schema，再透過 Google Cloud Application Default Credentials 呼叫 Vertex AI Gemini。Gemini 必須產生 `get_validated_study_plan` function call，程式驗證參數與原需求一致後才執行確定性排程，最後把工具結果回送 Gemini 整理說明。後端另保留 `STUDY_AGENT_PROVIDER=openai` 的 Responses API 介面供後續切換，但不取代課堂規定的 Gemini／ADC 主證據。
2. **畢業缺項說明：** 一般程式先計算學分與缺項；Gemini 只取得去識別彙整，輸出會經固定規準評估，最多修正一次。說明具有 300 秒 TTL 與來源重驗證，失效時回退基本進度。

模型不決定正式學分、衝突、權限或寫入結果。規則引擎、Gate、版本檢查、到期、撤回與冪等都由一般程式處理。provider 失敗時，畫面仍保留安全的規則結果。

目前沒有正式登入、課表自動匯入或校務系統連線；課表與畢業條件使用本機示範／測試資料。沒有 ADC 或 Google Cloud project 時，真實主流程必須標示 `LIVE_NOT_RUN`，不得以 fixture 冒充。

Week 06 的兩條 workflow 與 Week 07 的兩種記憶控制分別整理於 [`docs/week06/README.md`](docs/week06/README.md) 與 [`docs/week07/README.md`](docs/week07/README.md)。

### 期中報告版本

- 繳交用 PDF 與可編輯 PPTX：[`reports/midterm/`](reports/midterm/README.md)。
- 報告架構、課程概念對照與測試結果：[`docs/midterm/`](docs/midterm/README.md)。
- GitHub 分支盤點與整合判定：[`docs/midterm/BRANCH_INTEGRATION.md`](docs/midterm/BRANCH_INTEGRATION.md)。
- 主示範工具：`get_validated_study_plan`，唯讀預覽；模型參數必須通過後端驗證。
- 寫入工具：`save_study_plan`，必須 `confirmed=true` 並以 `request_id` 防止重複寫入。
- 真實 Gemini／ADC 證據：`docs/midterm/evidence/study-agent-live.json`。

## Acceptance Criteria（驗收條件）

### 1. 課表與截止事項顯示

- **Given：** 專案已載入固定的本機示範課表與截止事項。
- **When：** 使用者開啟「今日／本週」。
- **Then：** 系統顯示課程名稱、上課時間、地點與截止日期，並可切換週檢視與日檢視。

### 2. 待辦與私人行程管理

- **Given：** 系統已載入本機示範課表。
- **When：** 使用者新增、修改或刪除待辦事項與私人行程。
- **Then：** 行事曆同步更新；若新增或修改後的行程與既有課程重疊，顯示衝突提醒。

### 3. 自動安排複習

- **Given：** 使用者已設定考試日期、所需複習時數及可安排時段。
- **When：** 使用者要求 AI Agent 規劃複習。
- **Then：** 系統在考試前的空閒時段安排指定時數，且不與既有行程重疊；時間不足時，顯示尚缺的時數。

### 4. 畢業進度追蹤

- **Given：** 後端已載入固定測試使用者、啟用中的 `nutn-csie-115-integrated-v2` 規則與合成修課紀錄。
- **When：** 使用者查看畢業進度或明確要求產生缺項說明。
- **Then：** 一般程式先顯示每項已取得、尚缺或待確認狀態；模型說明不得把未知當成零、把規劃中課程算成已取得，且來源更新或 300 秒到期後停止使用。

## 後端 API

Flask＋SQLite 已提供使用者資料、課程查詢、學生安排與已確認偏好 API。React 會從 `/api/v1` 讀寫待辦、私人行程、讀書時段、115 修課規劃、課表、課程、已修紀錄、畢業規則及 `study_session_minutes`；舊版四組 `localStorage` 只在第一次啟動時作為遷移來源，成功後即移除。啟動方式見 [後端 README](backend/README.md)，契約與限制見 [學生安排 API](docs/api/student-planner.md)。目前仍是固定測試使用者，尚未建立正式登入。

## 前端原型

可操作的前端原型位於 [`frontend/`](frontend/README.md)。目前使用本機示範資料，提供課表、待辦與行程、複習規劃、修課規劃、畢業進度及兩個校區的地圖檢視。啟動與測試方式請見前端 README。

主示範需要同時啟動 Flask 與 Vite：

```bash
./scripts/init-backend-db.sh
./scripts/run-backend.sh

# 另一個終端
./scripts/select-demo-profile-115.sh
cd frontend
npm install
npm run dev
```

網站課程規劃與畢業門檻以「115 學年度」清楚標示，執行規則為 [`nutn-csie-115-integrated-v2`](nutn_csie_115_graduation_rules.json)。共同認列範圍仍為 `null`，所以已通過課程會保存為已修紀錄，但在認列前不會冒充已取得畢業學分。

本機 ADC 設定使用 `gcloud auth application-default login`；專案只讀取 `GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION` 與 `GOOGLE_CLOUD_GEMINI_MODEL`，不得提交 ADC JSON。

## 先前提案

### 1. 租屋媒合 - 組員1

- **Problem：** 學生在準備搬家或找租屋處時，退租與招租資訊分散在不同社群，難以確認空房時間、租金及屋況，需要逐一詢問。
- **Target user：** 即將退租、希望分享房源的學生，以及準備在學校附近租屋的學生。
- **User Story：** 身為準備租屋的學生，我希望找到即將退租且符合預算與入住時間的房源，並向原租客了解居住經驗，以便更快找到適合的住處。

### 2. 二手書交易 - 組員3

- **Problem：** 學生修完課後，課本常被閒置；需要課本的學生則難以找到符合課程與版本的二手書，必須在社群中逐篇搜尋與詢問。
- **Target user：** 有閒置課本想出售或贈送的學生，以及需要購買課本的學生。
- **User Story：** 身為有閒置課本的學生，我希望上架書籍的名稱、版本、書況與價格，讓需要的人能搜尋並聯絡我，以便讓課本再次被使用並回收部分購書費用。

### 3. 拼車 - 組員2

- **Problem：** 學生週末前往火車站時，獨自搭計程車的費用較高，即使有其他同學同時出發，也難以找到時間與路線相近的人共同搭車。
- **Target user：** 週末返家、需要從學校或住處搭車前往火車站的學生。
- **User Story：** 身為週末要搭火車返家的學生，我希望找到出發時間與地點相近的同學一起叫車，以便分攤車資並準時抵達車站。

### 4. 課表與學習規劃 - 組員3

- **Problem：** 學生的課表、作業期限與私人行程分散在不同地方，安排讀書時間時需要反覆核對，容易遺漏待辦事項或將複習集中在考前。
- **Target user：** 需要同時安排課程、作業、課外活動與考試複習的大學生。
- **User Story：** 身為需要兼顧課業與活動的學生，我希望整合課表、待辦事項與考試日期，依照空堂時間和學習進度安排複習，以便掌握每日任務並提前準備考試。

### 5. 學分與畢業進度追蹤 - 組員4

- **Problem：** 學生在選課或確認畢業資格時，需要自行比對修課紀錄與適用的畢業規定，容易漏算學分類別、未修必修課或講座次數，影響後續選課安排。
- **Target user：** 需要規劃選課及確認畢業進度的大學生，尤其是大三、大四學生。
- **User Story：** 身為正在規劃畢業的學生，我希望查看已取得的各類學分，以及尚缺的必修課、講座與其他畢業條件，以便提前安排修課並如期畢業。

## 本機後端開發環境

Flask 與 API 測試網頁已建立於 `backend/`，啟動、測試、環境重建與完整移除方式請見 [後端說明](backend/README.md)。已提供固定測試使用者＋SQLite 的 `GET /api/v1/me`、`PATCH /api/v1/me`；[API 規格與實測證據](docs/api/me.md) 記錄契約、限制與測試結果。前端個人安排已串接同一個 Flask／SQLite 後端；正式登入與多使用者隔離仍未完成。

另提供 `GET /api/v1/semesters`、`GET /api/v1/courses`、`GET /api/v1/courses/{id}`、`GET /api/v1/course-offerings` 四支唯讀測試資料 API；查詢條件、資料庫升級方式及實測結果見 [課程查詢 API 文件](docs/api/catalog.md)。

## 規則整合與變更紀錄

- [113 學年度來源與整理界線](docs/sources/113-academic-year/README.md) 與後端展示規則 `backend/app/data/nutn_csie_113_graduation_rules_v1.json`。
- [專案決策與變更紀錄](docs/decisions/CHANGE_DECISIONS.md)：逐項決定、新舊差異、影響分支與檔案，後續變更持續追加。
- [115畢業規則整合說明](GRADUATION_PROGRESS_115.md) 與 [唯一整合JSON](nutn_csie_115_graduation_rules.json)。
- 115 整合規則是目前網站執行規格，最低 133 學分；舊 `nutn-csie-115-mvp-v1` 與 113 規則只保留為版本化歷史／回歸資料。合成修課紀錄仍不可當作真實學生畢業資格。

## Week 07：畢業說明記憶範圍（C 路線）

[作業說明、程式差異、測試與證據索引](docs/week07/README.md)。本週對既有畢業缺項說明加入五分鐘 TTL、來源重查與工作階段清除；不改畢業判定。離線證據已提供；真實 Gemini 為 LIVE_NOT_RUN，正式跨 user 驗收為 NOT_RUN，完成提交不代表所有功能驗收通過。
