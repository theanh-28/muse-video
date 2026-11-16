# PROMPT 01 — Tạo một tập phim

Hãy tạo một episode mới trong dự án này từ brief sau. Trước tiên chỉ làm tiền kỳ; KHÔNG gọi video generation.

## Brief
- Ý tưởng: [MÔ TẢ Ý TƯỞNG]
- Thể loại: [THỂ LOẠI]
- Khán giả: [ĐỐI TƯỢNG]
- Độ dài mục tiêu: [SỐ PHÚT]
- Tỷ lệ: [16:9 / 9:16 / 1:1]
- Phong cách hình ảnh: [MÔ TẢ]
- Ngôn ngữ thoại: [NGÔN NGỮ]
- Số nhân vật chính: [SỐ LƯỢNG]
- Ghi chú/điều cấm: [NẾU CÓ]

## Deliverables
1. Logline và synopsis.
2. Script phân cảnh có thoại/narration/action/SFX.
3. Character Bible và World/Location Bible.
4. Continuity locks cho tạo hình, trang phục, đạo cụ và bối cảnh.
5. Storyboard dạng JSON và bản Markdown dễ duyệt.
6. Mỗi shot có start_state, action beats, end_state, camera, lighting, sound, references, prompt và negative constraints.
7. Continuity dependency graph: shot nào phải đợi shot nào.
8. Danh sách asset cần tạo và asset hiện có.
9. Generation manifest dự kiến, không gửi request.

## Quy tắc
- Không tạo thêm nhân vật/đạo cụ không có trong kịch bản.
- Mỗi shot chỉ có một hành động chính dễ quan sát; chia shot khi hành động hoặc camera phức tạp vượt khả năng clip.
- Prompt phải mô tả diễn biến theo thời gian nhưng không liệt kê quá nhiều hành động không thể thực hiện trong một clip.
- Giữ nguyên cụm continuity locks đã chốt.
- Viết shot N+1 dựa trên end_state dự kiến của shot N; sau khi có video thật phải cập nhật bằng trạng thái quan sát được.
- Đánh dấu rủi ro continuity và shot cần ảnh tham chiếu.
- Trình bày để người dùng duyệt trước khi tạo media.
