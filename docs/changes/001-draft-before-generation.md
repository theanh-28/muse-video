# Mốc 1 — Tạo brief chỉ lập bản nháp

## Quyết định và lý do

Trước thay đổi, form bật Auto-Pilot sẵn. `POST /api/runs` thiếu `autopilot` cũng mặc định `true`. Worker sau đó tự duyệt storyboard, manifest, gửi Muse và chấp nhận continuity review. Người dùng chưa có dịp xem kế hoạch cụ thể trước request đầu.

Từ mốc này, hành động tạo phim chỉ lập bản nháp. Quyền duyệt storyboard và gửi từng shot vẫn là các hành động riêng. Quyền batch sau khi xem kế hoạch sẽ được thiết kế ở mốc sau.

## Hợp đồng vận hành

- Nút trên form là **Tạo bản nháp**. Brief được gửi đến backend sáng tạo đã cấu hình. Bước này chưa gửi video tới Muse.
- `POST /api/runs` thiếu `autopilot` hoặc có `autopilot: false` lưu run rồi chỉ lên lịch `analyze_run`. Khi phân tích thành công, trạng thái là `DRAFT_READY`.
- `POST /api/runs` có `autopilot: true` trả HTTP 422 với hướng dẫn duyệt kế hoạch. Request bị từ chối trước khi lưu run hoặc lên lịch công việc.
- Dữ liệu run cũ thiếu trường `autopilot` hoặc có giá trị `true` vẫn đọc được. Trang lịch sử chỉ hiển thị trạng thái đã lưu.
- Các bước duyệt storyboard, manifest, usage/budget và xác nhận `SEND <manifest-id>` của một shot tiếp tục dùng đường thủ công hiện có.

## Kiểm tra đã chạy

- `rtk proxy .\.venv\Scripts\python.exe -m pytest tests/test_studio_draft_gate.py -q --basetemp D:\muse-animation-studio-starter\test_tmp_m1 -p no:cacheprovider` — 5 passed. Fixture thay thế hàm phân tích ở ranh giới background task và kiểm trạng thái qua API. Hai fixture run cũ giữ `SUBMITTED` và task ID.
- `rtk proxy .\.venv\Scripts\python.exe -m pytest tests -q --basetemp D:\muse-animation-studio-starter\test_tmp_m1_all -p no:cacheprovider` — 39 passed, 4 skipped. Các ca gửi thủ công và hash manifest sẵn có nằm trong bộ này.
- `rtk proxy node --check src/animation_studio/studio/static/app.js` — exit 0.

## Giới hạn xác minh

Test API dùng phân tích giả trả `DRAFT_READY`; chưa chạy backend sáng tạo thật. UI được kiểm qua HTML/JS và cú pháp Node, chưa chạy trình duyệt. Không gửi request Muse, Kokoro hoặc LLM trong mốc này. Các test media cần FFmpeg được skip trong môi trường kiểm thử. Quy tắc batch sau duyệt và hồ sơ nhân vật/giọng thuộc các mốc sau.
