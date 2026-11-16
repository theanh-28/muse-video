# PROMPT 00 — Khởi động dự án với Codex

Bạn là AI Animation Director, Story Editor và Senior Automation Engineer. Hãy bắt đầu xây dựng dự án trong thư mục hiện tại theo các quy tắc tại `AGENTS.md`.

## Mục tiêu sản phẩm
Xây dựng một pipeline tự động hóa video hoạt hình nhiều cảnh:

**Codex lập ý tưởng/kịch bản/đạo diễn → tạo prompt theo từng shot → Muse tạo clip chuyển động → kiểm tra continuity → FFmpeg ghép và xuất MP4.**

Codex là bộ não sáng tạo và điều phối. Muse chỉ đảm nhiệm tạo media chuyển động. FFmpeg làm hậu kỳ tuyến tính. Không dùng Remotion để mô phỏng chuyển động nhân vật.

## Việc cần làm theo thứ tự

### Phase 0 — Audit trước khi code
1. Đọc `AGENTS.md`, toàn bộ `docs/` và cấu hình mẫu.
2. Kiểm tra OS, Python, uv, Node (chỉ khi cần Skills), FFmpeg/ffprobe, dung lượng ổ đĩa.
3. Kiểm tra Codex có nhận diện Skills hay chưa.
4. Audit ba Skills/repository được ghi trong `docs/THIRD_PARTY_SKILLS.md`; không cài mù quáng. Đề xuất bộ Skills nhỏ nhất, ít trùng lặp nhất.
5. Audit `muse2api` upstream: API schema, auth/session, cookie storage, task lifecycle, reference image/video input, duration/aspect ratio limits, media download, error handling, security and license.
6. Kiểm tra xem Muse video generation có truy cập được từ tài khoản người dùng hiện tại không. Ghi rõ bằng chứng và ngày kiểm tra. Không giả định quyền truy cập hoặc 1B referral tokens được dùng qua gateway.
7. Chưa gửi generation request, chưa cài dịch vụ không cần thiết và chưa tạo chi phí ở Phase 0.

### Phase 1 — Architecture and decision record
Viết:
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/ADR/0001-provider-integration.md`
- `docs/ADR/0002-continuity-strategy.md`

So sánh ba phương án:
A. Muse2API local gateway (experimental).
B. Muse web thao tác thủ công, Codex quản lý prompt/clip.
C. Video provider chính thức có API (nếu sau này có và người dùng chấp thuận).

Chọn phương án MVP dựa trên kết quả audit, không dựa trên giả định. Nêu rủi ro, giới hạn và điều kiện rollback.

### Phase 2 — MVP CLI, chưa cần Dashboard
Xây dựng CLI Python với các lệnh tương đương:
- `project init`
- `episode init`
- `storyboard validate`
- `prompts build`
- `generation plan` (chỉ tạo manifest, không gửi request)
- `generation submit` (chỉ chạy sau xác nhận rõ ràng)
- `generation status`
- `media inspect`
- `continuity update`
- `episode render`
- `episode qc`

Giữ provider interface độc lập. Nếu Muse2API chưa xác minh được, triển khai ManualProvider để workflow còn dùng được mà không giả vờ gọi API.

### Phase 3 — Continuity-first generation
1. Mỗi shot có start_state/end_state và continuity_level.
2. Shot nối tiếp phải được tạo tuần tự.
3. Sau mỗi clip, tải MP4, chạy ffprobe, trích first/middle/last frame.
4. Chỉ sau khi review clip thực tế mới cập nhật ledger và viết prompt tiếp.
5. Nếu provider hỗ trợ native snapshot continuation, kiểm thử trước. Nếu không, dùng last-frame reference nếu hỗ trợ. Nếu không hỗ trợ ảnh tham chiếu, dùng prompt-only continuity và match cut, đồng thời ghi rõ rủi ro.
6. Không khẳng định giữ nguyên khuôn mặt hoặc seamless continuity khi chưa có kết quả chứng minh.

### Phase 4 — Một tập MVP
Tạo một dự án demo cấu hình được; mặc định 1 nhân vật chính, 1 bối cảnh, 5–8 shot khoảng 10 giây/shot (thời lượng phải theo capability thật). Chỉ tạo media sau khi người dùng xác nhận manifest và đồng ý mức sử dụng.

### Phase 5 — Export and quality gate
Dùng FFmpeg/ffprobe để:
- kiểm tra stream/container, duration, resolution, FPS;
- phát hiện file lỗi và black frames cơ bản;
- nối clip theo cut list;
- ghép voice/music/SFX/subtitle;
- xuất MP4 và QC report.

## Yêu cầu kỹ thuật
- Python 3.11+ và uv.
- Pydantic cho model, PyYAML cho cấu hình, Typer cho CLI.
- Không thêm FastAPI/React/Redis cho đến khi chứng minh cần thiết.
- Không thêm Remotion, Blender, Godot hoặc Three.js vào MVP.
- Có unit tests cho schema, continuity rules, queue state và FFmpeg command construction.
- Mọi file output được ghi vào thư mục dự án; source asset không bị ghi đè.
- Không để credential trong source hoặc project docs.

## Cách báo cáo
Sau Phase 0, dừng và trình bày:
1. Tình trạng môi trường.
2. Skills đã cài/chưa cài và lý do.
3. Tình trạng thực tế của Muse video trên tài khoản.
4. Kết quả audit Muse2API và rủi ro.
5. Phương án provider được chọn.
6. Kiến trúc và implementation plan.
7. Các quyết định cần người dùng duyệt trước khi tạo video.

Không tuyên bố đã tạo video, đã gọi API hoặc đã kiểm thử nếu chưa thực sự thực hiện.
