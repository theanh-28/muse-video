# Quy trình sản xuất một tập

## Phase A — Development
1. Nhận brief, thể loại, đối tượng khán giả, độ dài và format.
2. Viết logline, premise, synopsis và beat sheet.
3. Viết script; tách thoại, narration, action và sound cues.
4. Tạo Character Bible, World/Location Bible và Prop Bible.
5. Tạo continuity locks: ngoại hình, trang phục, phụ kiện, palette, tỷ lệ, dấu hiệu nhận diện.
6. Chia shot theo nhịp hành động. Không chia cơ học theo số giây; chia theo hành động có mở/diễn biến/kết thúc rõ.

## Phase B — Storyboard and prompt package
Mỗi shot phải có:
- shot_id, sequence_id, planned_duration, target aspect ratio.
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
