# Tool Usage Notes
Chữ ký công cụ được cung cấp tự động thông qua function calling.
Tệp này ghi lại các ràng buộc và cách sử dụng không hiển nhiên.

## exec — Giới Hạn An Toàn
- Các lệnh có thời gian chờ có thể cấu hình (mặc định 60 giây)
- Các lệnh nguy hiểm bị chặn (`rm -rf`, format, `dd`, shutdown, v.v.)
- Đầu ra bị cắt ngắn ở mức 10.000 ký tự
- Cấu hình `restrictToWorkspace` có thể giới hạn quyền truy cập tệp chỉ trong workspace

## cron — Nhắc Nhở Theo Lịch
- Vui lòng tham khảo kỹ năng cron để biết cách sử dụng.
