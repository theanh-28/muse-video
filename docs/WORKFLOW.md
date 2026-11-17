# Quy trình sản xuất một tập

## Dùng giao diện local

Có thể nhập brief trong web app và để Codex CLI tạo Bible/storyboard DRAFT. App tự kiểm tra schema, lưu project riêng, tạo prompt đầu tiên sau khi storyboard được duyệt, rồi chuẩn bị one-shot manifest. Tại mỗi request Muse vẫn cần review prompt/usage/budget và xác nhận gửi riêng; sau khi clip hoàn tất, app tự poll, tải, inspect, conform, trích frame và QC.

Continuity review gửi ba frame mẫu qua Codex chỉ khi người dùng bấm nút. Ledger chỉ được ghi sau khi người dùng xem và chấp nhận assessment. Sau đó app mới tạo prompt cho shot kế tiếp từ actual end state và last frame. Episode chỉ export khi mọi shot cần thiết đã review và QC_PASSED. Hướng dẫn chạy: [USER_GUIDE_WEB.md](USER_GUIDE_WEB.md).

## Phase A — Development
1. Nhận brief, thể loại, đối tượng khán giả, tổng thời lượng và format. Agent tự chọn số shot và thời lượng từng shot theo các beat cần kể; không giao quyết định này cho người dùng.
2. Viết logline, premise, synopsis và beat sheet.
3. Viết script; tách thoại, narration, action và sound cues.
4. Tạo Character Bible, World/Location Bible và Prop Bible.
5. Tạo continuity locks: ngoại hình, trang phục, phụ kiện, palette, tỷ lệ, dấu hiệu nhận diện.
6. Chia shot theo nhịp hành động. Agent chọn số shot và phân bổ độ dài theo nội dung; không chia cơ học theo số giây hoặc chia đều tổng thời lượng trừ khi đó là chủ đích nhịp điệu. Mỗi shot là một Muse video request, tối đa 10 giây. Nếu hành động dài hơn, tách tại beat có ý nghĩa thành nhiều shot và giữ continuity.

## Phase B — Storyboard and prompt package
Mỗi shot phải có:
- shot_id, sequence_id, planned_duration không quá 10 giây cho mỗi request Muse, target aspect ratio.
- mục đích kể chuyện.
- nhân vật xuất hiện (on-screen/off-screen).
- trạng thái bắt đầu và kết thúc.
- blocking: vị trí tương đối, hướng cơ thể/hướng nhìn, tay cầm đạo cụ.
- một hành động chính và các micro-beats.
- shot size, angle, lens/look, camera movement, focus.
- ánh sáng, môi trường, âm thanh, thoại.
- reference plan (ảnh nhân vật, location, previous last frame).
- negative constraints và continuity locks.
- điều kiện pass/fail QA.

Sau khi storyboard được duyệt, dùng `anistudio-muse-prompting` để Codex soạn prompt một shot từ dữ liệu đã duyệt, reference và actual end state đã review. Lưu đúng nguyên văn prompt vào `episodes/<EP>/prompts/` và hiển thị trong manifest trước khi gửi.

## Phase C — Preflight
1. Probe tính năng provider: duration, aspect ratio, reference images, continuation ID, audio, resolution.
2. Kiểm tra assets tồn tại và filename an toàn.
3. Kiểm tra prompt/storyboard khớp duration và scene cast.
4. Xuất generation manifest liệt kê chính xác số request và tham số.
5. Đo usage trước thử nghiệm nếu có thể.
6. Chỉ gọi generation sau khi người dùng xác nhận batch.

## Phase D — Sequential production
1. Tạo shot đầu tiên.
2. Tải file và xác thực media bằng ffprobe.
3. Trích first/middle/last frames.
4. Review những gì thực sự xuất hiện; cập nhật continuity ledger.
5. Tạo shot tiếp theo từ trạng thái thực tế và reference phù hợp.
6. Không tiến hành shot phụ thuộc nếu shot trước lỗi hoặc chưa được review.

## Phase E — Editing and export
1. Dựng cut list dựa trên shot durations thực tế.
2. Chuẩn hóa codec, resolution, frame rate nếu cần.
3. Ghép video; trộn voice/music/SFX; tạo phụ đề từ script hoặc alignment thực tế.
4. Xuất MP4; kiểm tra video/audio streams, duration, black frames và audio clipping.
5. Lưu QC report, file nguồn và manifest.

## Phase F — YouTube packaging (optional, after export)
1. Chỉ bắt đầu khi MP4 cuối có `EXPORTED` và QC `PASS`.
2. Dùng skill `yt-package`, `yt-thumbnail` và `yt-seo` để tạo title/thumbnail pairing, concept thumbnail, description, tags và hashtag từ frame của MP4 thật cùng continuity ledger.
3. Nếu người dùng cung cấp transcript timestamp đã khớp với MP4 và helper tìm được boundary hợp lệ, dùng thêm `yt-chapters`; nếu thiếu transcript, video dưới 30 giây hoặc boundary không hợp lệ, ghi rõ lý do bỏ chapter.
4. Lưu các bản nháp vào `episodes/<EP>/metadata/draft-<timestamp>-<id>/`. Người dùng kiểm tra nội dung và timestamp trước khi sử dụng. App không upload hoặc publish.
