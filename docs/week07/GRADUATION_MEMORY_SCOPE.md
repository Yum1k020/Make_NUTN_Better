# Week 07 — 畢業說明的到期與來源更新控制

## 目標

選用 Route C，替模型衍生的畢業缺項說明增加 300 秒有效期限、來源指紋、工作階段 scope 與舊回應防護。這項功能不更動畢業判定、學分採計、規則版本或 Week 06 的 A/B 評估規準。

## 主要行為

- 說明自伺服器讀取來源開始最多有效 300 秒，重查不延長期限。
- 來源指紋包含畢業進度與規則 digest，排除每次變動的 `evaluated_at`。
- Gemini I/O 前後都比對來源；來源改變或生成期間到期時回傳 stale 並移除說明。
- 前端每 15 秒及 focus/visibility 恢復時重查；重查中先隱藏舊說明，失敗時清除。
- 新工作階段、離開頁面或重新整理會清除頁面記憶；較早的非同步結果不得復原已清除內容。
- `scope_id` 存在 Flask 簽章的 HttpOnly、SameSite=Strict session cookie，不包含姓名、學號或成績。

## 資料界線

| 資料 | 位置與生命週期 |
| --- | --- |
| 修課、講座與畢業規則 | 原 SQLite，不因說明到期而刪除 |
| 說明、來源指紋、run ID、期限 | 畢業頁記憶，不寫 localStorage 或長期資料表 |
| scope ID | 瀏覽器 session cookie，程序重啟可能失效 |
| 測試 trace | Git 只保留合成資料與清理後證據 |

到期與清除只停止新使用，不保證刪除截圖、第三方日誌、瀏覽器開發工具或備份。scope 也不是登入授權；正式跨 user 案例仍需補驗證。

## 重現

```bash
./.venv/bin/python -m pytest -c backend/pytest.ini \
  backend/tests/test_graduation_validity.py \
  backend/tests/test_graduation_explanations.py

cd frontend
npm test
npm run build
```

真實 provider 狀態必須另執行 `backend/week07_acceptance.py --live`。匯入證據為 `LIVE_NOT_RUN`，不得以 fixture 取代。
