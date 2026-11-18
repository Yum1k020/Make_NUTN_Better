# Week 09 Evidence Index

## Versions

- Baseline branch：`codex/backend-persistence`
- Baseline SHA：`cf7376f97c6a85129c796580957df589512e2ef2`
- Verified implementation SHA：`be1afdac6f61f6a1ec00c6890f75b0013bdba0b3`
- Method：Few-shot Prompting
- Baseline context：`week08-instruction-v1`
- Candidate context：`week09-few-shot-v1`

## GitHub Actions

- Week 09 run：`44216456067`
- Week 09 job：`134507385419`
- Week 09 artifact：`14388587457`
- Week 08 regression run：`44216456091`
- Week 08 regression job：`134507386238`

## Results

| Evidence | Result |
| --- | --- |
| Focused backend tests | 15 passed |
| Offline same-case comparison | offline_all_pass=true |
| Frontend tests | 41 / 41 passed |
| Vite production build | PASS |
| Prettier | PASS |
| Week 08 regression workflow | PASS |
| Real provider same-case comparison | LIVE_NOT_RUN |

## Same-case outputs

Committed：`week09/evidence/offline_comparison.json`

這是 `OFFLINE_INJECTED`，用來證明：

- Baseline / Candidate 收到相同 expert packet。
- 兩版使用相同 deterministic plan。
- context version 確實不同。
- 同一固定 evaluator 能比較兩版。

它不代表真實 OpenAI 模型品質提升。

## Real provider

Runner：`python -m week09.live_compare`

需要私有 `OPENAI_API_KEY`。成功後會輸出 `W09-LIVE-*.json`；只有實際送出兩版 provider calls 才能標示 `LIVE_PASS`。
