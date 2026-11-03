# Week 07 Baseline vs Memory Candidate

Baseline SHA：9e2407a9a9a160b5ca5b51fc6e4a090ba077768e

Implementation SHA：72380961e4d096b8d334d87d53546f750d4292ac

| 比較項目 | Baseline | Route A candidate |
|---|---|---|
| 新 session 的 session_minutes | 必須重新提供 | 缺值時讀有效偏好 |
| 偏好來源 | 無持久偏好來源 | source_type + source_id |
| owner 隔離 | N/A | PASS：另一 user forbidden |
| 更正 | N/A | PASS：v1 superseded，讀 v2 |
| 撤回 | N/A | PASS：revoked 後 not_found |
| 到期 | N/A | PASS：expires_at 後不回填 |
| 未確認寫入 | N/A | PASS：confirmation_required，0 write |
| 同 ID 重送 | N/A | PASS：replayed=true，0 duplicate |
| 原 scheduler | scheduler_v1 | 不修改 |
| 固定業務終點 | study-plan preview | PASS：仍排滿 180 分鐘 |
| 真實 Gemini | 本週 baseline 不另跑 | LIVE_NOT_RUN |

## CI

- Run 40618188523 → success
- Job 122585522782
- 31 passed, 1 xfailed
- offline_all_pass=true
- Artifact 12786022642

## 三層結果

1. 檢索是否讀對：owner、最新版、未撤回、未過期皆受控。
2. 回答是否用對：只有本輪缺 session_minutes 時才使用記憶；明確輸入優先。
3. 任務是否完成：仍使用原 preview_study_plan；偏好不取代 busy interval、exam date 或其他業務規則。

calls、tokens、latency 只在 Week 07 真實 Live 後報告；未量測不推定。


---

## 畢業功能線文件（原始分支內容）

# 原版與候選比較

比較的兩個版本：整合基線 `32ec10231d70448ca43013036eec1f0869a21ce8`；候選程式 `6d97f7e8b969253bf4b3ef52df9db36959105c0a`。基線是 develop 加既有 Week 06 的合併結果，不包含本週新增功能。

固定資料：一門完成且明確通過的3學分課程、一門修習中、一門規劃中；專業講座10、一般講座未知。使用相同課程、規則、resource ID、時間戳記與 fixture provider；資料庫副本各自隔離。provider固定輸出通過原規準的結構化內容。兩版都使用 langgraph，原終點相同；合成更新在兩個版本的同一個provider階段執行。

| 三層品質／成本 | 原版 | 候選 |
|---|---|---|
| 正常讀取 | 已得3學分，未知仍null | 與原版正常進度完全相同 |
| 正常回答 | 通過原 evaluator | 同規準通過；加上scope與期限 |
| 生成期間來源更新 | 仍將先前資料標為verified，來源已過時 | stale／SOURCE_CHANGED，explanation為空 |
| 到期後使用 | 沒有TTL契約 | 300秒後排除；生成期間到期也拒絕 |
| 新scope與舊回應 | 無獨立世代防護 | 清除後晚回應不復原，導覽卸載後不回寫 |
| 原任務終點 | 顯示啟用規則下的缺項，不認證畢業 | 保留同一終點；失效時要求重新產生 |
| 正常合成模型呼叫 | 1 | 1 |
| 模型tokens | fixture不提供，不適用真實用量 | 同左；不寫成0 |
| 正常合成延遲 | 944ms | 991ms |
| 額外代價 | 無週期來源重查 | 每15秒一次唯讀檢查，初始與生成另有檢查 |

上述延遲是本機fixture單次觀測，**不能推論真實模型變快或省錢**。來源檢查不增加模型呼叫，但會增加資料庫計算與HTTP負擔。實際數值、run ID及候選內容雜湊見 [comparison.json](evidence/comparison.json)、[baseline.json](evidence/baseline.json)、[candidate.json](evidence/candidate.json)。

前端同時驗證 TTL邊界、重查不展延、來源更新、session改變、重查失敗、舊生成／舊重查回應、卸載、明確reset及server在生成期間判定到期。不是只驗證新增欄位存在。

**採用：條件採用於本機原型。** 離線品質改善有證據；C01真實Gemini與C02正式跨user仍未完成，不宣稱整體作業功能通過。亦未實測大量並行、多程序部署、來源推播或當期真實學生資料。

公開證據僅含控制流程、測試結果及內容雜湊；完整合成HTTP/學業payload不發布。請執行已提交的fixture runner重現細節。這是資料省略，不是以摘要冒充真實Gemini或跨user通過。
