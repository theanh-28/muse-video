# Ghi chú nghiên cứu công cụ (đối chiếu 16/11/2026)

## 1. Drama Skills — nền tảng tiền kỳ

Repository: https://github.com/zenstory-ai/drama-skills

- README mô tả 12 Skills, đi từ ý tưởng/nguyên tác đến kịch bản tập, storyboard, prompt ảnh/video, sản xuất, dựng và review.
- README tiếng Anh ghi rõ hoạt động với Codex và các agent hỗ trợ Agent Skill spec.
- Tác giả mô tả 5 tài liệu sáng tạo làm nguồn sự thật: script, visual design, storyboard, image prompts, video prompts; cut list khi dựng.
- Có continuity locks cho tạo hình/trang phục, prompt preview và xác nhận trước khi gọi API tạo media.
- Cài project-local theo hướng dẫn README: `npx skills add zenstory-ai/drama-skills -y` (không thêm `-g`). Kiểm tra kết quả cài trên máy trước khi tiếp tục.
- License hiển thị trên GitHub: MIT. Giữ nguyên LICENSE và attribution khi sao chép bất kỳ phần nào.

## 2. Muse Video Prompt Skill — tham khảo riêng cho Muse

Repository: https://github.com/masonmosen/muse-video-prompt-skill

- Skill mô tả workflow prompt → generation → multi-segment stitching → frame verification.
- SKILL.md đề cập prompt 6 phần, chia clip dài thành nhiều đoạn, tham chiếu continuation/snapshot ID và trích frame để tự kiểm tra.
- Tài liệu nói không cam kết lock-face; tham chiếu ảnh không bảo đảm giữ nguyên gương mặt.
- SKILL.md nêu đơn clip 10 giây là giới hạn trong workflow của tác giả; phải xác minh lại trên tài khoản/provider thực tế, không coi là bảo đảm toàn hệ thống.
- README/SKILL có ghi Muse built-in video generation gặp lỗi region 403 và lần kiểm tra được ghi ngày 05/11/2026. Đây là báo cáo của maintainer, không phải trạng thái đã được xác minh trên tài khoản của người dùng vào ngày hiện tại. Phải probe thực tế trước khi thiết kế automation.
- License hiển thị: MIT. Giữ nguyên LICENSE và attribution.

## 3. Universal Video Skills — kiến thức điện ảnh trung lập model

Repository: https://github.com/svenkatreddy/universal-video-skills

- Mô tả hỗ trợ Muse, Claude, Grok, Gemini và Agent Skills clients khác.
- Phạm vi gồm prompt craft, cinematic direction, storyboarding, character consistency, dialogue/audio, assembly, model adapters và QA.
- Đây là bộ kỹ năng/hướng dẫn, không phải model AI. Nội dung được thực thi bởi model đang chạy trong Codex.
- GitHub đang hiển thị license MIT. Kiểm tra cây Skills, phụ thuộc và nội dung thực tế trước khi import; không coi độ phổ biến/star count là bằng chứng chất lượng.

## 4. Muse2API — tích hợp thử nghiệm, không chính thức

Repository: https://github.com/czg86389-hub/muse2api

- README mô tả reverse-engineer giao diện Muse và bọc thành OpenAI-compatible REST API, thông qua headless browser/CDP, session management; có text/image/video generation.
- Đây không phải API chính thức của Meta. Web UI thay đổi có thể làm integration hỏng.
- Có xử lý session/cookie. Cần đọc kỹ cách lưu và bảo vệ credential; không commit dữ liệu đăng nhập.
- Không mở gateway public; mặc định chỉ localhost. Không sử dụng account rotation để tránh hạn mức.
- Chỉ tích hợp sau khi người dùng chấp nhận rủi ro và một video tạo thật thành công. Không khẳng định Additional Tokens referral chắc chắn dùng được qua gateway; đo Usage trước/sau trên tài khoản.
- GitHub hiển thị MIT, nhưng license repository không đồng nghĩa phương thức sử dụng được Meta cho phép theo điều khoản dịch vụ.

## Kiến trúc đề xuất

Codex + Skills → durable project files (Bible/Script/Storyboard/Continuity) → Provider Adapter (Muse2API experimental; manual workflow fallback) → inspect frames → continuity update → FFmpeg assembly.

Không lấy Remotion làm lõi tạo chuyển động nhân vật. Remotion chỉ là tùy chọn nếu sau này cần motion graphics hoặc template overlays phức tạp.

## Audit đối chiếu mã upstream (2026-11-16)

### Muse2API source

Read-only shallow checkout: `czg86389-hub/muse2api`, commit `19db32a3d6ef50dc87567a8ee0e35dd50c8f7837`; `app.py` khai báo phiên bản 1.6.11. Đã đọc `app.py`, `engine.py`, `config.py`, `store.py`, README và LICENSE; không chạy mã hay test upstream.

- FastAPI/Pydantic hiện thực định nghĩa schema: `VideoRequest` có prompt, model, duration, size, aspect_ratio, resolution và các trường media. Duration là `int | None` không có min/max; prompt builder dùng 6 giây nếu bỏ trống. Size/aspect/resolution không có range validation; chúng được chuyển thành yêu cầu prompt và không là cam kết output.
- `POST /v1/videos` hoặc `/v1/videos/generations` trả task đồng bộ hóa; worker nền ghi `queued`/progress, kết quả `completed` hoặc `failed`; `GET /v1/videos/{task_id}` poll; media được phục vụ dưới `/v1/media/{name}`. Store persist task metadata và tài khoản thành JSON.
- Mã hiện tại chấp nhận image/video/audio/files là reference qua các field tương ứng. Giới hạn gateway: tối đa 10 reference, 40 MiB mỗi file, 100 MiB tổng; reference video cần duration metadata phân tích được, các định dạng được nhận bị giới hạn 120 giây. Đây là giới hạn file tham chiếu, không phải clip output.
- Request model không có continuation/snapshot ID. Không khẳng định native continuation. API bearer key xác thực gateway; Muse cookie/session của tài khoản lưu trong `data/accounts.json` dưới dạng JSON; cần bảo vệ như password. Mặc định host là loopback.
- README khai báo MIT. License mã gateway không xác nhận chấp thuận dùng reverse-engineered UI theo điều khoản dịch vụ. Không có usage endpoint/contract đủ để cam kết referral token hoặc tính chi phí.
- Lịch sử upstream có issue về video attachment đến muộn bị báo failed sớm trên v1.6.4 (issue #35, 2026-10-31); HEAD audit có test late-attachment nhưng không được chạy. Đây là tín hiệu rủi ro task lifecycle, không phải kết luận phiên bản hiện tại còn lỗi.

### Official Meta API check

Tra cứu tài liệu Meta Model API ngày 2026-11-16: tài liệu chính thức mô tả Muse Image generation và Muse Spark video understanding; không tìm thấy video generation endpoint trong tài liệu đã xem. Xem [Meta Model API overview](https://dev.meta.ai/docs/overview), [image generation](https://dev.meta.ai/docs/image-generation) và [video understanding](https://dev.meta.ai/docs/media-understanding). Điều này không chứng minh Meta sẽ không phát hành API tương lai.

### Third-party skills

Audit commit/license/status và bản mở rộng local: xem `THIRD_PARTY_SKILLS.md`. Ba nguồn được tham khảo tại commit đã pin và ánh xạ có chọn lọc vào skills project-local; upstream packages/scripts không được cài hoặc chạy. Muse Video account access, capabilities và kết quả generation phải tiếp tục được xác minh riêng; skill audit không thay thế probe tài khoản.
