# ADR — 為智慧學習加入一位受限 Study Load Review Expert

## Status

ADOPT_OFFLINE / LIVE_NOT_RUN. Verified implementation SHA `16a0ec65c4027fa13c9f63e20a895de65f7d9b36`; CI run `42939439673` passed focused backend tests, 40/40 frontend tests, production build and formatting.

## Context

智慧學習已經有可驗證的單一 Agent 基線：

- request schema
- tool parameter Gate
- deterministic scheduler
- Flask／SQLite
- React UI
- provider fallback

Week 08 要形成真正的 multi-agent 增量，但不能因為課堂主題而把整個系統不必要地拆成多角色。

## Decision

採 Route A：原 Study Coordinator 保留控制權，只加入一位 Study Load Review Expert。

專家不重新排程、不使用工具、不寫資料，只閱讀最小、去識別的排程封包，檢查負荷與剩餘時數，再回傳 Coordinator。

## Why not Centralized with two experts

目前只有一個已量測且清楚的額外責任：讀書負荷審查。硬拆成兩個以上專家只會增加模型呼叫、同步和整合成本，沒有對應瓶頸證據。

## Why not Handoff

使用者仍在同一個智慧學習流程中；專家只做限定子任務，不應取得整段對話或最後答覆權。因此 Agent-as-tool / return semantics 比 Handoff 合理。

## Safety boundaries

- deterministic planner 仍是時間事實唯一來源。
- model tool args 必須等於已驗證 request。
- expert 不取得 personalEvents 原文。
- expert request 不宣告任何 tools。
- expert 沒有 DB write。
- expert 與 deterministic facts 矛盾時拒絕。
- provider／expert 失敗時前端仍保留先前規則排程 fallback。

## Cost

正常路徑從原本兩次 provider calls 增為三次：

1. Coordinator tool selection
2. Expert review
3. Coordinator final summary

因此不宣稱更省 token 或更快。Week 08 要量測的是角色責任、上下文隔離與可觀察協作，不是假設 MAS 一定優於 SAS。

## Rollback

移除 expert review step 並回到原 `StudyAgentService` 的 tool selection → deterministic tool → summary，即可回復 baseline；資料庫 schema 無需回滾。
