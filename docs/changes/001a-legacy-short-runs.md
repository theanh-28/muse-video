# Mốc 1a — Đọc run lịch sử ngắn hơn 20 giây

## Lỗi và quyết định

Trước sửa, `StudioRun` dùng `StudioBrief` có giới hạn 20–180 giây. Một run 12 giây đã được workspace chính chấp nhận trước đây sẽ không qua Pydantic khi đọc từ đĩa. Việc đọc lịch sử giờ dùng `StudioBrief` với khoảng 1–180 giây. Route tạo mới dùng lớp `CreateStudioBrief` kế thừa cùng schema và giữ giới hạn 20–180 giây của baseline. Không đổi JSON cũ hoặc các trường khác.

## Kiểm tra

Chạy `rtk proxy D:/muse-animation-studio-starter/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'D:/muse-animation-studio-starter/.worktrees/m1/src'); import animation_studio.studio.service as s; print(s.__file__); import pytest; sys.exit(pytest.main(['tests/test_studio_draft_gate.py','-q','--basetemp','D:/muse-animation-studio-starter/.worktrees/m1/test_tmp_a','-p','no:cacheprovider']))"` trong worktree.

Kết quả 8 passed, 1 warning. Module service được nạp từ worktree Mốc 1. GET đọc các record 12, 1 và 19 giây, giữ đúng thời lượng, trạng thái, task ID và tiến độ khi có. Không gọi backend. POST mới 12 giây trả 422 trước khi lưu run; 20 giây qua bước kiểm tra đầu vào và gọi backend giả. Giới hạn: test dùng backend giả và chưa chạy trình duyệt.
