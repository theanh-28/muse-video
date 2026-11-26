# Mốc 1 — Tạo brief chỉ lập bản nháp

## Quyết định

Ở baseline Git `a15892a2714b450ef338d9bda15f8770bbf6bb68`, `POST /api/runs` đã chỉ lên lịch `analyze_run`. Working tree của workspace chính có Auto-Pilot chưa commit, bật sẵn trên form và tự duyệt/gửi. Mốc này xác lập hợp đồng đầu vào rõ ràng trên một branch riêng: tạo run chỉ lập draft, còn `autopilot: true` bị từ chối trước khi lưu run. Quyền batch sau khi người dùng duyệt kế hoạch thuộc mốc sau.

## Hành vi và tương thích

- Form dùng nút **Tạo bản nháp**. Backend sáng tạo lập storyboard; bước này chưa gửi video tới Muse. Nút hiển thị trạng thái đang tạo rồi trở lại nhãn ban đầu cả khi thành công và khi gặp lỗi.
- `POST /api/runs` thiếu `autopilot` hoặc có `false` lưu run và chạy `analyze_run`. Draft hợp lệ được lưu thành `project.yaml`, Bible, `episode.yaml` và queue trống. Run kết thúc ở `DRAFT_READY`.
- `POST /api/runs` có `autopilot: true` trả HTTP 422 với thông báo yêu cầu duyệt kế hoạch. Không tạo run hoặc task.
- Dữ liệu lịch sử thiếu trường `autopilot` vẫn đọc với mặc định `false`. Record có `autopilot: true` và các trường tiến độ vẫn được model chấp nhận, giữ nguyên trạng thái và task ID khi đọc. Từ chối `true` chỉ xảy ra ở route tạo mới.
- Đường duyệt storyboard, manifest, usage/budget và xác nhận `SEND <manifest-id>` của một shot tiếp tục dùng cơ chế baseline.
- Test đường lưu draft thật phát hiện baseline gọi nhầm `shutil.mkdtemp`, nên mốc này dùng `tempfile.mkdtemp` để draft có thể lưu được.

## Bằng chứng kiểm thử

Chạy trong worktree `D:/muse-animation-studio-starter/.worktrees/m1` bằng Python của `.venv` ở repo chính, sau khi đặt `sys.path` tới `.../.worktrees/m1/src` trước khi import package. Lệnh xác minh đầy đủ:

`rtk proxy D:/muse-animation-studio-starter/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'D:/muse-animation-studio-starter/.worktrees/m1/src'); import animation_studio.studio.service as s; print(s.__file__); import pytest; sys.exit(pytest.main(['tests','-q','--basetemp','D:/muse-animation-studio-starter/.worktrees/m1/test_tmp_verified2','-p','no:cacheprovider']))"`

Kết quả **40 passed, 4 skipped, 1 warning**. Module được import từ `D:/muse-animation-studio-starter/.worktrees/m1/src/animation_studio/studio/service.py`. Sáu test Mốc 1 đã chạy với FastAPI/httpx. Hai request hợp lệ chạy background task thật, qua validator thật, lưu và đọc lại `episode.yaml` DRAFT, queue trống, không có manifest. Test còn kiểm 422, hai dạng run lịch sử, và bốn trường hợp của `submit_generation`: chưa duyệt, sai câu xác nhận, manifest đổi, gửi hợp lệ đúng một lần qua fake CLI. `rtk proxy node --check src/animation_studio/studio/static/app.js` exit 0.

## Giới hạn

LLM và CLI submit được thay bằng fake trong test. Không gọi Muse, Kokoro hay LLM thật. UI được kiểm qua HTML/JS và API; chưa chạy trình duyệt. Bốn test media được skip trong môi trường này. Warning đến từ deprecation của Starlette TestClient/httpx.
