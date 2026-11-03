# Make NUTN Better — new-develop

組員：蔣仲鋰、張華庭、陳苾妏、呂安婷

## 分支範圍

本分支彙整 develop、Python Agentic Week02–07、前端 Node Agent 與畢業 Week05–07；使用 merge 保留每週歷史。`codex/integrate-agentic-week07` 保持獨立，未作為合併來源，其專屬 Node 偏好面板未納入。

這是成果合併版本，尚未完成 Flask／SQLite 架構統一。原本前端行程仍使用 localStorage；讀書 Agent 使用 Node／OpenAI；畢業頁使用 Flask／SQLite／Gemini；Python Agentic 腳本仍可獨立執行。不得把歷史測試紀錄當作此版本的實測。

## 安裝與啟動

需要 Python 3.12+、Node.js 22+。以下從專案根目錄執行。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-new-develop.txt
.venv/bin/python -m flask --app backend.app init-db
GRADUATION_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173 .venv/bin/python -m flask --app backend.app run --host 127.0.0.1 --port 5000
```

另一個終端機：

```bash
cd frontend
npm ci
npm run dev -- --config vite.graduation.config.js --host 127.0.0.1 --port 5173 --strictPort
```

開啟 http://127.0.0.1:5173；Flask API 文件在 http://127.0.0.1:5000/docs。畢業專用 Vite 設定保留 Node Agent middleware，並將 `/api/v1` 代理到 Flask。一般 `npm run dev` 不會自動加上這個代理。

- 畢業檢查預設 legacy；可用 `GRADUATION_ENGINE=langgraph` 切換。
- Gemini 現有接頭使用後端 `GEMINI_API_KEY`／`GEMINI_MODEL`，尚未改為 Google Cloud ADC。
- Node Agent 使用伺服器端 `OPENAI_API_KEY`／`OPENAI_MODEL`，設定方式見 [前端 README](frontend/README.md)。
- 未設定模型時不代表真實驗證成功；畢業頁提供基本說明回退。
- 初始化資料不足時應顯示待確認，設定方式見 [畢業與 Agentic Week06 文件](docs/week06/README.md)。

## 驗證

```bash
.venv/bin/python -m pytest -c backend/pytest.ini backend/tests
.venv/bin/python -m pytest -c pytest_agentic.ini tests
cd frontend
npm test
npm run build
```

共同環境使用 Agentic 的 LangGraph 1.2.15；畢業分支舊的 `backend/requirements-framework.lock.txt` 保留作歷史重現，不與共同需求檔同時安裝。原始套件版本需要獨立環境。

## 文件索引

- [合併來源、限制與本次驗證](docs/integration/new-develop.md)
- [後端服務](backend/README.md)
- [Python Agentic 進度](AGENTIC_AI_PROGRESS.md)
- [Week05 排程](week05/README.md)
- [Week05 畢業流程](docs/week05-graduation/acceptance.md)
- [Week06 累積文件](docs/week06/README.md)
- [Week07 累積文件](docs/week07/README.md)
- [排程 Week06 比較](docs/week06/AGENTIC-COMPARISON.md)
- [畢業 Week06 比較](docs/week06/comparison.md)
- [原 README 合併保存內容](docs/integration/source-readmes.md)

規則執行仍用後端 mvp-v1；根目錄 integrated-v2 是尚待遷移的目標規格。來源 README 快照內的相對連結以原根目錄為基準，請優先使用上方入口。
