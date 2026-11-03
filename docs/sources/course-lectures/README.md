# 第 3–7 週課堂投影片來源

整理日期：2026-11-03

本機使用 Microsoft MarkItDown 從課堂 PDF 抽取 Markdown，供專案概念對照與報告撰寫使用。PDF 是課堂來源，不是本專案自行產生的內容；引用時應註明週次與投影片標示頁碼。為避免重新發布完整課堂教材，轉換後的全文由 `.gitignore` 排除，GitHub 只保存本來源清單、雜湊與專案自行整理的概念對照。

| 週次 | PDF 檔名 | 本機轉換檔（不提交） | PDF SHA-256 |
| --- | --- | --- | --- |
| Week 03 | `Lecture03_Agentic_AI_Engineering_RAG.pdf` | `lecture03-rag.md` | `9f923b22938677eff30b1b9926cabe087f9e267263596cbe40ee749af5a2a5f4` |
| Week 04 | `Lecture4_Agentic_AI_Engineering_Tool_Use_MCP.pdf` | `lecture04-tool-use-mcp.md` | `cb7943d9d9ea4e91fd02fd455f6d927dcdab4d0795d915c946c001d0625fb279` |
| Week 05 | `Lecture05_Agentic_AI_Engineering_Frameworks_Orchestration.pdf` | `lecture05-frameworks-orchestration.md` | `e6eaa339d23db4c062d20a3158293b5791d26d3119e54052a9b7d3af1c580a2d` |
| Week 06 | `Lecture06_Agentic_AI_Engineering_Agent_Design_Patterns_Scaffolds.pdf` | `lecture06-agent-design-patterns.md` | `ac31b2e7d2669c15dce44ec18afb59bc143235782b978c530c5b513c66b910f2` |
| Week 07 | `Lecture07_Agentic_AI_Engineering_Agent_Memory_Architectures.pdf` | `lecture07-agent-memory.md` | `83f4370071aa373a260f248fd5f9d5caec45547ce95c868ec4ef85aea50e7e9b` |

## 使用界線

- Markdown 只用於搜尋與摘要；圖表、頁面編號及版面結論以原 PDF 為準。
- 下游文件使用投影片右下角標示頁碼，例如 Week 03 的 `5 / 54`，不以 Markdown 行號當作引用頁碼。
- 課堂案例中的羽球館、日期、價格、模型執行狀態與本專案證據彼此獨立，不得直接當成本專案已完成的證據。
- 本專案是否完成某概念，仍以程式、測試與執行紀錄為準；不能因投影片提到某技術就宣稱專案已實作。
