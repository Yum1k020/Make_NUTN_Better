# 一頁重構決策｜畢業規劃 × LangGraph

日期：2026-10-14 ｜ 決策：保留原版預設，候選供驗收；模型 live 待完成。

## 替換範圍
基準 c06b69f50d4ee66cdc38cf43e1843057c0728f3c。替換 planner_graduation.py::progress 的畢業進度編排，接回原 GET /api/v1/graduation-progress 與 dashboard 的畢業摘要。LangGraph 1.0.3 StateGraph 管理讀規則、彙整、分配、條件檢查、摘要及缺規則分支。

## 保留責任
保留原有規則文件 checksum、版本、學分分類、必修對照、學程／講座門檻、使用者歸屬、唯讀交易與錯誤回應。修習中／計畫課程不算已得學分；缺資料維持待確認，缺規則學分為 null。抽出業務 helper 與 GraduationState 轉接；未改成模型判定畢業資格。

## 同條件證據
8/8 A/B 通過：已得 3 學分、缺規則、24 學分分配為系選修 12＋自由選修 12、講座缺 1 場、合成 133 學分全達標、分類未知、規則 checksum 錯誤及資料庫故障。兩版僅排除 evaluated_at 後逐值等價；原始時間保留。重送、dashboard 摘要與資料庫不變皆核對。原 commit 與候選各 262 passed／4 skipped／3 deselected。證據見 docs/week05-graduation/evidence/。

## 實測得失與成本
流程分支及節點可觀察，原 API 與安全條件維持。代價為框架依賴、state、轉接與圖設定，並為獨立對照保留部分重複業務程式。短流程尚無省工或效能優勢證據；不以單次時間排名。相依版本固定於 requirements-framework.lock.txt；一次套件未來預設變更警告需留意升級回歸。

## 回退與下一步
GRADUATION_ENGINE=langgraph 可展示；改 legacy 並重啟回退，不遷移資料庫。Windows／Python 3.12／真實 LangGraph 與 SQLite 實測，非外部網路 E2E；3 項 POSIX pipe 測試排除。前端串接、正式登入、模型 live／語意、持久化恢復未驗證。依講義未 live 要標待完成，不宣稱 LIVE_PASS。先定義有來源的畢業缺項說明任務、共用模型接頭與授權額度，再評估下一階段。

依據：教授投影片 61、63、67～70（PDF 實體 59、61、65～68）；LangGraph 官方 Graph API。133 學分為既有版本規則；合成達標不等於校方正式認證。
