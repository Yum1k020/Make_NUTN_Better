# Week 04 Action Readiness

## READ — preview_study_plan
- 用途：只產生複習排程預覽，不寫入資料。
- 必填：plan_id、start_date、exam_date、target_minutes、session_minutes、allowed_windows、busy_intervals。
- 執行前：日期合法、需求分鐘與每次分鐘 > 0、可用時段與 busy interval 起訖有效。
- 成功證據：suggested_sessions、scheduled_minutes、remaining_minutes、reason、mutated=false。
- 停止條件：輸入錯誤立即停止；時間不足只回 remaining_minutes，不硬塞。

## WRITE — save_study_plan
- 用途：把已預覽、已確認的複習時段寫入本機合成 JSON。
- 模型不得自行提供 confirmed / request_id；兩者由 Runtime 管理。
- 未確認：accepted=false、executed=false，不建立檔案。
- 確認後：status=saved、request_id、saved_session_ids。
- 相同 request_id 重送：replayed=true，不重複寫入。
- 相同 request_id 對不同 payload：停止並回報 mismatch。
- WRITE timeout / unknown state：先查 store / audit，不換新 request_id 盲目重做。
