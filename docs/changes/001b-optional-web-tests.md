# Mốc 1b — Test web với dependency tùy chọn

## Lỗi và sửa đổi

`tests/test_studio_draft_gate.py` từng import `fastapi.testclient` trước khi kiểm môi trường. Pytest dừng lúc thu thập test khi thiếu FastAPI hoặc HTTPX. File nay gọi `pytest.importorskip` cho đúng hai package trước import `TestClient` và `web_app`. Bộ test provider cũng import HTTPX ở đầu file; file đó dùng cùng cơ chế skip cho nhóm dependency HTTP tùy chọn. Dependency bắt buộc của ứng dụng không thay đổi.

## Kiểm tra thực tế

Chạy trong `D:/muse-animation-studio-starter/.worktrees/m1`, luôn đặt `.../.worktrees/m1/src` lên đầu `sys.path` trước khi import package.

- Đầy đủ FastAPI/HTTPX: `rtk proxy D:/muse-animation-studio-starter/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'D:/muse-animation-studio-starter/.worktrees/m1/src'); import animation_studio.studio.service as s; print(s.__file__); import pytest; sys.exit(pytest.main(['tests','-q','--basetemp','D:/muse-animation-studio-starter/.worktrees/m1/test_tmp_full','-p','no:cacheprovider']))"` — **42 passed, 4 skipped, 1 warning**. Module service in ra đường dẫn worktree; tám test Studio chạy thật.
- Mô phỏng thiếu FastAPI/HTTPX bằng subprocess Python riêng, chặn import đúng hai package qua `builtins.__import__` trước `pytest.main(['tests', ...])` — **34 passed, 5 skipped**, không lỗi collection. Hai module test cần dependency tùy chọn được skip; các skip media theo môi trường tiếp tục có hiệu lực. Không tháo package khỏi `.venv` dùng chung.

Giới hạn: kiểm UI vẫn ở mức HTML/JS và API; chưa chạy trình duyệt. Mô phỏng import thiếu được chạy trong tiến trình cô lập, không phải môi trường cài package tối thiểu thực sự.
