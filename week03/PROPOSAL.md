# Week 03 — Retrieval Proposal

## User / Situation
使用「學生個人安排系統」的大學生，在查看畢業進度時會詢問適用的畢業門檻。

## Claim
> 115 學年度入學的南大資工系學生，第一版畢業審核最低總學分是多少？

這是一個應由外部／版本化規則資料支持的 claim，不應讓 LLM 自己猜。

## Data Scope
本週只使用 repo 內：

`backend/app/data/nutn_csie_115_graduation_rules_v1.json`

並產生 stable chunks：
- `grad-total-credits`
- `grad-lecture-counts`
- `grad-program-count`
- `grad-scope-disclaimer`

## Retrieval Baseline
- character bigram overlap
- domain term boost
- deterministic ranking
- fixed threshold
- `index_version=week03-transparent-v1`

這不是 production 向量搜尋，也不宣稱等同 embedding / hybrid retrieval。

## Refusal Conditions
- query 超出規則資料範圍
- required aspect 沒有被 selected evidence 覆蓋
- source 不存在或格式不合法

拒答時回 `INSUFFICIENT_EVIDENCE` 或 `MISSING_REQUIRED_ASPECT`。

## Fixed Queries
1. normal
2. paraphrase
3. no-answer
4. multi-evidence

## Evidence
```powershell
py week03\run_retrieval.py
py week03\run_generator_comparison.py
```
