# 畢業規劃前後驗收

2026-10-14，Windows / Python 3.12 / LangGraph 1.0.3。OFFLINE_NO_LLM，模型呼叫 0。

|案例|預期|原版|候選|
|---|---|---|---|
|partial|已得 3、尚缺總學分 130；修習中與計畫課程不計|PASS|PASS|
|missing_rule|needs_confirmation；學分 null；RULE_UNAVAILABLE|PASS|PASS|
|overflow|24 學分拆為系選修 12＋自由選修 12，不重複計|PASS|PASS|
|lecture_gap|合成 133 學分已足，但一般講座仍缺 1 場；not_met|PASS|PASS|
|full_met|合成 133 學分＋明確對照與講座；全部檢查 met|PASS|PASS|
|unknown_classification|已得 3；分類檢查 needs_confirmation|PASS|PASS|
|checksum_error|500 INTERNAL_ERROR，停止，不偽造結果|PASS|PASS|
|storage_error|500 INTERNAL_ERROR，停止，不改資料|PASS|PASS|

每組從同一 SQLite 複製 A/B；比對所有回應欄位，僅排除動態 evaluated_at，原值仍在完整 JSON。每組驗證資料庫前後 SQL dump SHA-256 相同、重送回應等價、dashboard 畢業摘要一致。nodes 為真實 logger 記錄。錯誤案例的 traceback 是刻意注入故障後的實際輸出，不代表測試失敗。

原始 commit 回歸：262 passed / 4 skipped / 3 deselected，47.22 秒（同一基準已執行證據）。畢業 LangGraph 候選重新執行：262 passed / 4 skipped / 3 deselected，45.27 秒，1 項套件未來預設警告。單次耗時含環境影響，不作效能結論。4 項 skip 為原有未實作功能；3 項 real_http 使用 POSIX pipe select，在 Windows 未選取。

規則來源沿用原專案 mvp-v1，總門檻 133。測試使用合成資料，包含測试用零學分學程對照，不能拿來宣稱真實學生達到正式畢業資格。缺分類會讓個別檢查待確認；整體沿用原版 not_met 優先序。

## 完整資料

- evidence/ab-evidence.json.gz：輸入、預期、實際回應、節點路徑、重送及 dashboard、雜湊。
- evidence/regression-baseline.json.gz：原始版本 HTTP／SQL trace 與逐項結果。
- evidence/regression-langgraph.json.gz：候選回歸；含實際測試來源 SHA-256。
- evidence/*.log：本次命令輸出；evidence/summary.json：摘要與環境。

Gzip 僅無損壓縮。可用 Python 解開：

```python
import gzip
from pathlib import Path
folder = Path('docs/week05-graduation/evidence')
for p in folder.glob('*.json.gz'):
    p.with_suffix('').write_bytes(gzip.decompress(p.read_bytes()))
```

原測試 hook 的 command 欄是 Linux 腳本標籤；實際 Windows 執行方式另記 actual_command。初次原版環境驗證遇到 UTF-8 JSON／cp950 錯誤，設定 PYTHONUTF8=1 後同條件通過；此次畢業比較全程沿用 UTF-8。

未完成：LLM live、自然語言語意、前端後端整合、正式登入、checkpoint／跨程序恢復。講義要求未 live 必須標待完成，所以不能將這些離線結果寫成 LIVE_PASS。
