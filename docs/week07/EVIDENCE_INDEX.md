# Week 07 證據索引

## 智慧學習偏好

| 證據 | 位置 | 可核對內容 |
| --- | --- | --- |
| Route A 實作 | `backend/week07_memory.py` | owner、版本、到期、撤回與冪等 |
| Route A 測試 | `tests/test_week07_memory.py` | 新 session、更正、撤回、跨 user、未確認、重送 |
| 離線比較 | `week07/evidence/offline_comparison.json` | baseline/candidate 與 `offline_all_pass` |
| Live runner | `week07/live_memory.py` | OpenAI proposal、人工確認、寫入、讀回與摘要 |
| Live 狀態 | `week07/evidence/LIVE_NOT_RUN.json` | 沒有 provider 憑證時不冒充成功 |

## 畢業說明有效性

| 證據 | 位置 | 可核對內容 |
| --- | --- | --- |
| focused | `docs/week07/evidence/focused.json` | 後端 TTL、來源與 scope 案例 |
| regression | `docs/week07/evidence/regression.json` | 後端可執行回歸與 skip 原因 |
| frontend TAP | `docs/week07/evidence/frontend.tap` | 前端記憶有效性測試 |
| build | `docs/week07/evidence/frontend-build.log` | production build |
| baseline/candidate | `docs/week07/evidence/baseline.json`、`candidate.json` | fixture 控制結果與 run ID |
| comparison | `docs/week07/evidence/comparison.json` | 來源更新、TTL、呼叫數與 fixture 延遲 |
| live | `docs/week07/evidence/live.json` | 歷史 `LIVE_NOT_RUN`，不是 OpenAI 成功證據 |
| UI fixture | `docs/week07/evidence/ui-fixture.png`、`ui-check.json` | 合成模式畫面與操作觀察 |
| summary | `docs/week07/evidence/validation-summary.json` | 測試數、平台限制與待補驗證 |

## 未完成與資料安全

- 正式跨 user 授權：`NOT_RUN`。瀏覽器 scope 不是登入使用者。
- 真實 OpenAI 正常流程：必須使用私有環境補驗證並依最新 evidence 判定。
- 沒有新增畢業紀錄寫入工具，因此 W01/W02 業務寫入案例不適用。
- 公開證據只保留合成資料、控制流程、雜湊與狀態，不得加入金鑰、憑證、真實個資或未清理日誌。
