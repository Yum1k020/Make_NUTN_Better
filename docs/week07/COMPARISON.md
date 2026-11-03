# Week 07 原版與候選比較總覽

## 智慧學習偏好 Route A

| 比較項目 | 原版 | 候選 |
| --- | --- | --- |
| 新 session 的每次複習分鐘數 | 必須重新輸入 | 缺值時讀取有效偏好 |
| owner 隔離 | 無長期偏好 | 跨 user 拒絕 |
| 更正與版本 | 不適用 | 新版本取代舊版本，舊版本寫入拒絕 |
| 撤回與到期 | 不適用 | 撤回或 30 天到期後不回填 |
| 重送 | 不適用 | 相同 operation ID 回放，不重複寫入 |
| 排程結果 | `scheduler_v1` | 同一規則重新計算，記憶不取代排程 |

細節與實際離線結果見 `week07/evidence/offline_comparison.json`。

## 畢業說明 Route C

| 比較項目 | 原版 | 候選 |
| --- | --- | --- |
| 來源在生成期間更新 | 可能顯示舊快照的說明 | `SOURCE_CHANGED`，清除說明 |
| 到期契約 | 無 TTL | 300 秒後排除，重查不展延 |
| 工作階段範圍 | 重新整理時清空 | 另有 scope 與非同步世代防護 |
| 正常模型呼叫 | fixture 1 次 | fixture 1 次，來源檢查不增加模型呼叫 |
| 讀取成本 | 無週期重查 | 每 15 秒一次唯讀檢查，另有初始與生成前後檢查 |
| 正式驗收 | 不適用 | 真實 OpenAI 依最新 evidence 判定；正式跨 user `NOT_RUN` |

匯入分支的單次 fixture 延遲只證明本機控制流程，不能推論真實模型變快或省錢。詳細內容見 `docs/week07/evidence/comparison.json`、`baseline.json` 與 `candidate.json`。
