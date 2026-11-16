# Continuity Specification

## 1. Nguồn sự thật
- Character Bible: danh tính và ngoại hình bất biến.
- World Bible: quy tắc thế giới, địa lý, ánh sáng, thời tiết.
- Prop Bible: trạng thái, vị trí và chủ thể đang giữ đạo cụ.
- Storyboard: ý đồ đạo diễn và trạng thái dự kiến.
- Continuity Ledger: trạng thái thực tế sau khi xem clip đã sinh.

Khi storyboard và clip thực tế khác nhau, ledger ghi nhận clip thực tế; Codex phải đề xuất sửa shot tiếp theo hoặc regenerate shot hiện tại. Không âm thầm giả định clip đã làm đúng.

## 2. Continuity locks
Tạo mã khóa ổn định như `CHAR-A-LOOK-01`, `COSTUME-A-RED-COAT`, `PROP-SWORD-01`, `LOC-ROOFTOP-NIGHT`. Mỗi lock có:
- locked description (cụm mô tả cố định, không tự diễn đạt lại).
- reference asset path.
- shot IDs áp dụng.
- mức độ: immutable / persistent / scene-specific.

## 3. Trạng thái mỗi shot
`start_state` và `end_state` ghi:
- vị trí tương đối trong frame và trong không gian.
- hướng mặt, hướng thân, eyeline.
- pose và trạng thái chuyển động.
- tay trái/phải và đạo cụ đang cầm.
- trạng thái trang phục/tóc/vết thương.
- vị trí props và điều kiện môi trường.
- camera position, angle, lens/look, motion phase.
- ánh sáng, thời tiết, time-of-day.
- cảm xúc và trạng thái câu chuyện.

## 4. Nối clip
Ưu tiên:
1. Provider native continuation / snapshot ID đã được probe và test.
2. Last-frame image reference + continuity prompt nếu endpoint hỗ trợ.
3. Prompt-only continuity + cut on action / match cut / establishing shot.

Nếu dùng last frame:
- trích frame cuối có nội dung hợp lệ; có thể trích thêm frame ở 0.5–1 giây cuối để tránh chọn frame motion blur.
- kiểm tra frame có bị đen, lỗi, chuyển cảnh hoặc che khuất không.
- dùng ảnh đó làm reference, đồng thời ghi rõ nó đại diện cho trạng thái nào.
- không yêu cầu clip mới lặp lại hành động đã hoàn tất; mô tả đúng điểm nối tiếp.

## 5. Mức độ continuity
- `C0`: độc lập, không yêu cầu khớp shot khác.
- `C1`: giữ style/nhân vật/bối cảnh.
- `C2`: giữ bố cục và vị trí tương đối.
- `C3`: nối hành động liên tục, khớp pose/camera/props.

Shot C3 không được song song với shot tiền nhiệm. Nếu provider không có continuation/reference, đánh dấu continuity risk và đề xuất cắt chuyển cảnh thay vì hứa nối seamless.
