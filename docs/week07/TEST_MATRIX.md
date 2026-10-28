# 測試矩陣｜預期與實際分開

所有 PASS_OFFLINE 使用合成資料／注入 provider；實際測試細節與 run ID 見 evidence JSON 及前端測試紀錄。

| ID | 預期 | 實際／狀態 | 證據 |
|---|---|---|---|
| C01 正常主流程 | 真實 Gemini 使用當次進度，來源、數字一致 | **LIVE_NOT_RUN**：未設定 GEMINI_API_KEY/GEMINI_MODEL；合成正常流程 PASS_OFFLINE | live.json、candidate.json |
| C02 跨 user | U002 看不到 U001 的記憶與答案 | **NOT_RUN**：原系統固定 user，未實作登入映射；不得將 browser scope 測試代替 | focused.json 的 skip；補做計畫見下 |
| C03 非法輸入／越界 | user/clock/規則不能由呼叫者覆寫；非法請求不呼叫模型 | PASS_OFFLINE：非法內容422、跨來源403，provider 0次 | focused.json、candidate.json.invalid |
| C04 服務失敗 | 有限停止，不保留錯誤或無法查證的說明 | PASS_INJECTED：沿用 provider 上限與 fallback；來源查詢失敗則清除 | focused.json、frontend.tap |
| C05 TTL | 到期邊界及生成期間到期都不能顯示舊說明 | PASS_OFFLINE：可控時鐘，無須等五分鐘；重查不展延 | focused.json、frontend.tap |
| C06 來源更新 | 講座或規則更新後舊結果失效 | PASS_OFFLINE：不同來源指紋；I/O期間變更回 stale/空說明；同ID合成規則內容變更也失效 | baseline.json、candidate.json、focused.json |
| C07 工作階段 | 新scope或卸載後不能恢復舊記憶 | PASS_OFFLINE：不同瀏覽器scope/reset不同；舊回應不能覆寫 | focused.json、frontend.tap |
| W01 未授權不寫 | 有新增業務寫入才測 | **N/A**：本路線未新增業務寫入，原學分資料保持不變；session reset另測入口拒絕 | candidate.json、focused.json |
| W02 同ID重送 | 有新增業務寫入才測 | **N/A**：沒有新業務寫入命令；來源重查不增加模型呼叫、不延長TTL | frontend.tap、focused.json |
| 其他路線 | A/B/D 的偏好、事件、共享 | **N/A**：只選 C，不把講義16案例全部套用 | ADR.md |

## 受阻項目的具體補驗證

1. C01：於後端設定私人 GEMINI_API_KEY/GEMINI_MODEL，執行 `python backend/week07_acceptance.py --live`。檢查 normal_kind=gemini、actual_call、來源、評估、usage與run_id；未過記 LIVE_FAIL，不手改 PASS。
2. C02：先由可信後端登入身分取得目前 user；將既有固定 DEMO_USER_ID 的所有資料入口改為該身分，再以兩個使用者與不同修課資料測試 API／UI／模型摘要拒絕交叉存取。此改造跨越既有全專案身分架構，這次沒有假裝完成。
3. 原有三項測試使用 POSIX pipe/select，在 Windows 出現 WinError 10038；最終回歸明確 deselect，沒有刪掉測試。後續在 Linux CI 執行，或另作 Windows 可攜改造。
4. 當期開課、共同認列範圍及目標 v2 規則遷移仍是原專題待辦，不以記憶功能猜測補齊。

公開證據僅含控制流程、測試結果及內容雜湊；完整合成HTTP/學業payload不發布。請執行已提交的fixture runner重現細節。這是資料省略，不是以摘要冒充真實Gemini或跨user通過。
