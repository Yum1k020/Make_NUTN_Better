# 專案決策與變更紀錄

本文件持續記錄規則、功能、合併與分支清理。記錄日期採 Asia/Taipei。
本次整理日期：2026-10-03。較早決策以本對話和 Git 提交為依據，不補造精確決策時間。

## 維護方式

每次新增或改變決策，追加一筆：編號、日期、問題、舊方案、新方案、最終決定、理由／來源、影響分支、影響檔案、資料遷移、驗證、發布狀態。
不得無聲覆蓋過去決策；如改變，標記取代哪個編號。程式實作、文件決定與正式校方規定分開記錄。歷史測試證據不改寫成新版本證據。
狀態：已決定／已寫入規則／已實作／已驗證／已推送／已合併；不可互相等同。

## 本次範圍與來源

- 工作分支：`docs/unified-graduation-rules`，起點 `main` 的 `4b13948a7c2451159a3055bf8d0024bc36b48dc4`。
- 舊資料：該提交的 `nutn_csie_115_graduation_rules_v1.json`（`nutn-csie-115-mvp-v1`）。
- 新資料：`docs/graduation-progress-115` 的 `058e83791c8886a17286b223d26a2e800ac76adc`：`nutn_csie_115_graduation_rules.json`、`GRADUATION_PROGRESS_115.md`（`nutn-csie-115-source-v1`）。
- 輸出：根目錄唯一整合規則 `nutn_csie_115_graduation_rules.json`，ID `nutn-csie-115-integrated-v2`；人可讀摘要 `GRADUATION_PROGRESS_115.md`。
- 舊根目錄 JSON 由本次刪除，原件與完整來源仍可用上述 Git 提交取得。新版來源分支不刪除，本次是內容整合，不是把整個來源分支執行 git merge。
- 現行後端 `backend/app/data/nutn_csie_115_graduation_rules_v1.json` 保留原樣作為執行相容快照，與整合規格用途明確區分。
- `feature/task-api-enhancements` 的待辦變更不包含於本次規則分支，保持獨立。
- 本次未重新讀取或核實原始校方 PDF；來源中的「文件規定」是輸入文件的引述，不能冒充本次校方查證。

## GR-001 學分與必修共同基礎

舊／新版一致：133總學分；通識核心12、選修18（領域至少12、至少三個領域、多元至多6）；科技法律2；專業必修69；專業選修至少12；自由選修至少20。
25門專業必修的代碼、名稱、學分與建議學期逐筆一致，完整保留。81／83學分小計保留作說明，不額外加總。
影響：整合JSON `/credit_requirements`、整合說明與 DATA_GUIDE。來源：兩版JSON所引115課程架構表。
狀態：已寫入規則；後端數字門檻本來即一致。

## GR-002 專業選修目錄採新版

舊版沒有35門完整選修參考目錄；新版有代碼、名稱、學分、建議年級。
決定：完整採用新版35門清單，不改課名或自創課程ID。目錄不等於每學期開課清單、學程採計清單或共同認列範圍；建議年級不保證開課。
影響：JSON `/course_catalog`，整合說明的課程表。未匯入 courses 資料表。

## GR-003 學程清單採舊版

舊版依114課程地圖列雲端網路11門、智慧計算10門、應用資訊10門；新版將年度與course_ids留空等待核對。
決定：保留舊版全部課名與三個學程識別；115入學使用114名單是團隊決策。正式ID需另外對照，不按相似課名猜測。
各學程至少三門不同的「已通過且已認列」指定課程，至少完成兩個學程。這裡的認列還受GR-010共同範圍限制。
影響：JSON `/program_requirements`；日後 backend/app/planner_graduation.py 的學程判定。

## GR-004 學程證書與課程進度分開，依修課推定

舊版只用通過課程數，不另審證書；新版要求兩個已驗證證書，修滿課不自動取得。
決策歷程：先列待確認 → 決定分開保存進度與證書 → 使用者確認課修滿即視為取得，即使證書原本未知 → 確認三門均須已通過且已認列。
最終：課程達標則 certificate_status=inferred_obtained，basis=project_course_completion；至少兩個學程達標即符合本系統學程條件。
這是團隊推定，不是實際校方驗證，不得標成officially_verified=true。課程不足為not_inferred（不等於證明沒有真實證書），資料不足為unknown。沒有新增紙本上傳、申請或審核流程。
影響：JSON `/program_requirements/certificate_policy`；未來後端保存／回應課程與證書狀態的結構、前端顯示及測試。
狀態：政策已寫入；證書狀態持久化尚未實作。

## GR-005 講座沿用兩類累計已通過場次

舊版：專業10、一般12，手動兩個數字；新版：專業10，逐場保存出席、心得與認可，不納入一般12。
決定：一般採舊版12，專業10；只需要知道已通過，最後選擇沿用總場次而非逐場紀錄。
professional_count/general_count代表已通過場次，不是單純出席；null是未知、0是明確零場；兩類分開，不互抵或重複採計。
不保存心得、不新增逐場資料表、不區分每場心得與活動審核狀態。輸入總數無法逐場檢查重複，這是已知限制。
影響：JSON `/lecture_requirements`、資料指南和講座欄位說明；現行 lecture_progress 表結構可沿用。
來源：專業門檻沿用文件；一般12及簡化保存方式是團隊政策。

## GR-006 自由選修來源採新版

舊版描述本系專業選修超額與合格外系選修；新版明列本系、外系、外校（國內外大學）、師培中心、通識中心的合格專業課程。
決定：採新版，但不是來源符合就自動採計；須通過共同認列範圍及自由選修分類／資格檢查。兩版都沒有完整自由選修課程清單。
影響：JSON `/credit_requirements/free_elective`；未來課程分類、採計與資料輸入。

## GR-007 專業選修超額自動分配

舊版採用先滿12、超額補自由選修；新版只標建議設計並要求認列。
決定A：確認已通過、已認列且符合自由選修資格後，自動將超過12的部分分配至自由選修，不需再人工確認一次。资格未知保留待確認。
同一學分只分配一次；學程門數與學分可以同時滿足；不把通識或未知分類超額任意轉列。屬團隊採用的分配政策，不宣稱本次已核實為校方算法。
影響：JSON `/credit_allocation`；未來畢業分配引擎與測試。

## GR-008 60分政策可選、預設停用

舊版明定數字成績60以上通過；新版建議選用且預設不啟用。
決定：保留threshold=60、enabled_by_default=false；不單憑分數推導通過。停用時明確passed狀態為依據，grade只保存；只有成績沒有通過結果時待確認，不能自動算通過。
影響：JSON `/passing_and_recognition/optional_numeric_threshold`、DATA_GUIDE。
後端現有 planner_logic.py 與 planner_core.py 仍有60分一致性檢查，未來遷移時需同步移除硬編碼／改政策控制，更新測試。

## GR-009 通過與認列分開

舊版依passed與分類判斷；新版增加recognition_status，通過不代表可採計。
決定：採新版概念，只有已通過且已認列才計入已確認學分及學程門數。狀態：pending_confirmation / recognized / not_recognized。
已認列仍不表示能任意歸到任何類別；需有效分類與學程對照。特殊抵免、重修等不在本次實作範圍。
影響：JSON `/passing_and_recognition`；未來修課資源欄位、規則判定、API/OpenAPI、UI與測試。當前Flask尚未支援獨立認列狀態。

## GR-010 一份共同認列範圍，範圍外不認列

新增團隊政策，非兩份原文件既有完整設計。
使用者將來提供一份共同範圍：範圍內recognized，範圍外not_recognized；不是每種類別各一份。進入範圍後，再依原有分類與三個學程清單決定用途。
尚未提供時用course_ids=null、status=not_provided、version=null，相關判斷待確認。不得把null當空清單；[]表示明確沒有任何課程可認列。35門選修與114學程名單不能自行充當共同範圍。
正式課程ID無法識別時屬資料不足，不能冒稱已完成範圍比對。
影響：JSON `/passing_and_recognition/common_recognition_scope`；後續需提供範圍、來源、版本與正式課程對照。
狀態：政策已決定；範圍尚未提供。

## GR-011 通識细節採新版

門檻不變；逐項檢查中文4、英文4、體育2、運算思維與AI2。英文與程式分級資料未知，不自行推定替代／免修。
領域至少12學分且涵蓋至少3個領域；每領域至少一門通過且採計的判準保留為provisional（待核對細則）。
多元至多6，不是必修6；補充微學分、自主募課、師培、校際選課、認可平台等可能來源，但需認列。平台或開課單位本身不等於採計資格。
影響：JSON `/credit_requirements/general_education`、DATA_GUIDE，未來通識分類與檢核。

## GR-012 不納入畢業模擬與GPA

新版提出假設規劃課程通過的模擬、可能畢業學期估計與停用的GPA設計；舊版沒有独立模組。
決定：本次先不要，不加入simulation/gpa執行設定；列入excluded_conditions，只計算實際進度。不新增模擬頁面、預估畢業日期或GPA算法。
影響：整合JSON與說明文件；不表示未來永遠不能重新提出。

## GR-013 保留每條規則來源

保留兩份輸入的固定提交與SHA-256、原文件引用的校方PDF名稱、團隊決策編號。
JSON policy_provenance以路徑記錄規則群與子項依據，更具體路徑優先；區分原文件引述、專案政策、暫定規則與待提供資料。
不沿用新版JSON內未核實的Markdown雜湊，直接對本次讀取的固定提交內容計算實際SHA-256。
影響：JSON `/sources`、`/policy_provenance`、本紀錄。沒有聲稱校方文件已重新驗證。

## GR-014 狀態與顯示

保留兩版一致的已達標／未達標／待確認；任一未達標則整體未達標，否則有待確認則待確認，全部啟用條件滿足才達標。所有細項仍顯示。
未知不是0，缺資料不得默默略過。百分比只表示學分進度，不能代替所有畢業條件。結果用「符合本次啟用的專案規則」，非正式校方畢業認證。
影響：JSON `/evaluation_contract`、未來結果顯示。

## GR-015 本次發布範圍

先完成決策紀錄，再產生一份整合規則與說明，更新指向；提交並推送 `docs/unified-graduation-rules`。
不直接覆蓋後端mvp-v1、不修改開發資料庫、不合併main、不刪除docs來源分支。以新ID及schema_version=2.0.0區分資料契約。
影響檔案清單：
- 新增 `docs/decisions/CHANGE_DECISIONS.md`（本文件，今後追加紀錄）。
- 新增 `nutn_csie_115_graduation_rules.json`（唯一整合規則）。
- 新增 `GRADUATION_PROGRESS_115.md`（整合說明及課程表）。
- 刪除根目錄 `nutn_csie_115_graduation_rules_v1.json`（由Git歷史保留）。
- 更新 `DATA_GUIDE.md`、`README.md`、`backend/README.md`（入口、現行／目標規則區分）。
- `backend/app/data/nutn_csie_115_graduation_rules_v1.json` 與後端Python不變。

## 先前已完成變更回溯

以下記錄先前已發生的事件；不把它們算成本次分支的新改動。

| 編號 | 決定與實際結果 | 影響分支 | 主要檔案／提交 |
| --- | --- | --- | --- |
| HIST-001 | 保存本機Flask學生規劃成果並推送 | 原feature/student-planner-api-flask | backend/app/planner*.py、測試、規則及文件；b79c78e |
| HIST-002 | C排程從main撤回，另保留功能分支 | main、feature/c-study-scheduler | C_scheduler_push/；原2b727b1，還原da20f73 |
| HIST-003 | Flask後端合併main | main | 4b13948；包含使用者、課程及學生規劃API |
| HIST-004 | 清除已合併功能分支，保留歷史 | 原feature/user-profile-api、feature/course-catalog-api、feature/student-planner-api-flask | 分支末端88c2beb、d32c99b、b79c78e；內容仍在main |
| HIST-005 | 舊FastAPI待辦功能移植Flask，舊分支封存後刪除 | feature/task-api-enhancements；原codex/student-planner-api | 7325482；描述5000字、三段優先級、無期限待辦、limit/offset、資料庫健康檢查、文件與測試；265通過4略過 |

HIST-005細節：保留Flask的task_id、due_date/due_time與data/meta；預設type=todo、description=""、priority=medium；分頁預設50最大200，保留截止日期順序；舊JSON讀取補新欄位，不改表；無期限不列入日期摘要。前端未串接；優先級不參與排程，同優先級細分尚無決策。原FastAPI與課堂羽球文件由tag `archive/student-planner-api-fastapi` 保留（80ead4c）。
`scheduler3`曾將Python放入LICENSE，最新同步時確認已不存在；本紀錄不推定刪除者。
Node/npm檢查與可乾淨移除的安裝方式曾討論，但本次不安裝，不宣稱前端已完成建置驗證。

## 驗證與發布紀錄

本次將檢查JSON有效性、25門必修與35門選修完整性、三個學程名單一致性、認列null/空清單區分、每項決策與来源對應、後端快照未變及舊連結處理。發布結果於完成時追加，後續程式遷移另立紀錄。

### 2026-10-03 本次檢查完成

JSON解析與政策斷言通過；必修25門共69學分逐筆等於兩版來源；35門專業選修逐筆等於新版；三學程11／10／10門逐筆等於舊版；共同認列範圍保持null；60分預設停用；無simulation/gpa設定；政策路徑與來源編號可解析；來源SHA-256吻合固定提交；更新文件的本機連結存在；git diff --check通過。後端相容快照與origin/main逐位元組一致，沒有程式或資料庫變更，因此未重跑後端測試，亦未宣稱新版規則已經後端驗收。

發布方式：本筆紀錄與整合文件一併提交至 `docs/unified-graduation-rules` 並推送同名遠端分支；不合併main。提交識別以該分支Git歷史為準，避免在檔案內記錄自身提交雜湊造成循環。
