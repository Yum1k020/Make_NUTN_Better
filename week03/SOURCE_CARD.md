# Week 03 — Data Source Card

## Source
- source: `backend/app/data/nutn_csie_115_graduation_rules_v1.json`
- owner in project: Make_NUTN_Better team
- purpose: 課堂展示系統的第一版畢業規則
- authority: 團隊依提供文件與既有決策整理；不是校方正式畢業資格認證

## Permission / Access
- 專題 repo 內規則檔
- 不包含 API key
- 不需要私人帳號資料
- 不把學生個人修課紀錄放進 retrieval corpus

## Freshness / Version
- 以 `schema_version`、`rule_set_id` 作為版本依據
- 規則更新後重跑 retrieval trace
- 舊 trace 不可當新規則 evidence

## PII
Corpus 不應包含姓名、學號、成績或私人行程。

## Withdrawal / Rebuild
更新或撤回來源後：
1. 更新規則檔
2. 重建 chunks
3. 重跑 fixed queries
4. 更新 trace 與 generator comparison

## Conflict Policy
來源衝突時不讓 generator 自行選邊；標記需人工確認。
