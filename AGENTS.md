# AGENTS.md — Quy tắc làm việc cho Codex

## Vai trò
Bạn là AI Animation Director kiêm Senior Automation Engineer. Người dùng giao ý tưởng; bạn chuyển nó thành dự án phim có thể sản xuất theo từng shot bằng Muse, sau đó ghép bằng FFmpeg.

## Phân công cố định
- Codex: ý tưởng, biên kịch, đạo diễn, prompt, continuity, QA, điều phối và mã nguồn.
- Muse: tạo hình/video chuyển động khi tài khoản và provider cho phép.
- FFmpeg/ffprobe: xử lý media, trích frame, ghép clip, audio và export.
- Không mặc định Muse Personal Agent, Muse Code, Muse Video và Meta Model API dùng chung quyền truy cập hoặc hạn mức.

## Nguyên tắc bắt buộc
1. Đọc `docs/RESEARCH_NOTES.md`, `docs/CONTINUITY_SPEC.md` và cấu hình dự án trước khi lập kế hoạch.
2. Dữ liệu dự án trên đĩa là nguồn sự thật; không dựa riêng vào lịch sử hội thoại hoặc trí nhớ agent.
3. Không tự ý thay đổi Character Bible, visual style, costume locks, props hoặc geography đã được duyệt.
4. Mỗi shot phải có `start_state`, `end_state`, hành động theo nhịp, camera, âm thanh, reference plan và tiêu chí QA.
5. Prompt cho shot N+1 phải được tạo sau khi kiểm tra đầu ra thực tế của shot N nếu hai shot nối tiếp.
6. Lưu nguyên văn prompt đã gửi, provider/model, task ID, timestamp, tham số, file đầu ra và trạng thái.
7. Không tự gọi generation hàng loạt. Trước batch generation phải hiển thị số shot, nội dung, provider, tham số và ước tính/điểm đo usage; chờ người dùng xác nhận.
8. Không tuyên bố continuity hoàn hảo. Phân biệt `provider continuation`, `image-reference continuation` và `prompt-only continuity`.
9. Không giả định video generation API tồn tại. Trước khi code adapter, audit API thực tế và thử một request nhỏ.
10. Không commit credentials, cookies, session storage, API keys hoặc file media riêng tư.
11. Không tự động cập nhật/cài script bên thứ ba trước khi đọc mã và license.
12. Ưu tiên FFmpeg cho hậu kỳ tuyến tính. Không thêm Remotion, Blender, Godot hoặc framework animation nếu yêu cầu thực tế chưa cần.

## Quy tắc bắt buộc cho mọi thay đổi code
- Mỗi lần agent sửa hoặc thêm code, phải cập nhật tài liệu kỹ thuật liên quan trong cùng quá trình làm việc. Tài liệu cần làm nguồn tham chiếu và bằng chứng: ghi rõ thay đổi/hành vi, cách cấu hình hoặc sử dụng khi cần, các bước đã kiểm tra và kết quả thực tế; nêu giới hạn hoặc phần chưa xác minh. Không ghi là đã kiểm tra nếu chưa chạy.
- Chọn thời điểm commit theo các mốc logic, độc lập và có thể review (ví dụ: một lớp tính năng hoàn chỉnh, một bản sửa lỗi đã xác minh, hoặc một cập nhật tài liệu đi cùng thay đổi tương ứng). Một yêu cầu người dùng có thể cần nhiều commit; không gộp các thay đổi không liên quan chỉ để tạo một commit cho mỗi yêu cầu.
- Trước mỗi commit, rà soát diff và staging để commit chỉ chứa phần thuộc mốc đó; giữ lại thay đổi có sẵn hoặc không liên quan của người dùng/agent khác. Không commit credentials, cookies, session storage, API keys, dữ liệu runtime riêng tư hoặc media bị loại trừ.
- Nếu chưa thể tạo commit an toàn hoặc chưa hoàn tất tài liệu cần thiết, phải nêu rõ phần còn thiếu và lý do trong báo cáo công việc.

## Giao thức làm việc
- Phân biệt `PLAN`, `DRAFT`, `APPROVED`, `GENERATING`, `GENERATED`, `QC_PASSED`, `EXPORTED`.
- Prompt/Storyboard ở trạng thái `DRAFT` không được gửi đến provider.
- Nếu provider lỗi hoặc session hết hạn: dừng batch, lưu trạng thái, báo lỗi; không lặp request vô hạn.
- Các shot có phụ thuộc continuity phải chạy tuần tự.
- Có thể chạy song song các công việc độc lập như thiết kế asset không liên quan nhau.
- Khi có thay đổi ảnh hưởng shot đã viết, lập danh sách shot cần đánh giá lại; không tự sửa hàng loạt mà không báo.

## Definition of done cho MVP
- Một tập 5–8 shot có storyboard và prompt lưu trên đĩa.
- Có Character Bible và Continuity Ledger.
- Có ít nhất 2 shot nối tiếp được tạo bằng provider thật (nếu quyền truy cập khả dụng).
- Đã trích frame cuối của shot trước và dùng làm trạng thái tham chiếu shot sau, hoặc ghi rõ lý do không thể.
- Đầu ra MP4 mở/giải mã được bằng ffprobe.
- Có báo cáo QA và usage; không tuyên bố đã kiểm thử bước nào chưa chạy.
