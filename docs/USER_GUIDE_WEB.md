# Hướng dẫn giao diện Muse Animation Studio

## 1. Giao diện làm gì

Giao diện là web app **local**, không phải dịch vụ cloud. Browser chỉ gọi server trên `127.0.0.1`. Codex CLI phân tích brief và trả về package có schema; ứng dụng kiểm tra package, tạo project DRAFT và dùng provider/FFmpeg hiện có cho các bước media.

Quy trình tự động chạy đến các điểm cần quyết định của bạn:

- Duyệt Bible và storyboard trước khi đổi trạng thái sang `APPROVED`.
- Duyệt chính xác prompt, provider, tham số, usage basis và budget cap trước mỗi video request.
- Xác nhận lần cuối bằng cụm `SEND <manifest-id>` trước khi gửi một request đến Muse.
- Sau khi gửi, app poll task, tải clip, ghi metadata, trích frame, chạy decode/QC và conform sang profile xuất.
- Codex chỉ xem first/middle/last frame khi bạn bấm nút review; bạn xem và xác nhận kết quả trước khi continuity ledger đổi.
- Shot tiếp theo được lập prompt từ actual end state và last frame đã review. Không tự gửi shot kế.
- Episode render chỉ chạy khi tất cả shot đã review và có trạng thái `QC_PASSED`.

## 2. Yêu cầu

- Windows PowerShell, Python theo `pyproject.toml`, `uv`, Docker Desktop.
- Codex CLI cài và đã đăng nhập bằng tài khoản Codex của bạn. Nếu `codex` không có trong PATH, đặt `ANISTUDIO_CODEX_EXE` thành đường dẫn `codex.exe` trước khi mở server.
- Muse2API đang chạy ở loopback, một tài khoản hợp lệ và `MUSE2API_API_KEY` trong environment của PowerShell mở giao diện.
- FFmpeg và ffprobe có trên PATH.

## 3. Khởi động

Terminal thứ nhất:

```powershell
Set-Location D:\muse2api-runtime
docker compose up -d --build
```

Terminal thứ hai:

```powershell
Set-Location D:\muse-animation-studio-starter
uv sync --extra web

$keyLine = Get-Content -Encoding utf8 'D:\muse2api-runtime\.env' |
  Where-Object { $_.StartsWith('MUSE2API_KEY=') }
if (-not $keyLine) { throw 'Không tìm thấy MUSE2API_KEY trong .env' }
$env:MUSE2API_API_KEY = $keyLine.Substring('MUSE2API_KEY='.Length)

uv run python -m animation_studio.cli.main web --open-browser
```

App mở `http://127.0.0.1:8765`. Giữ terminal chạy trong lúc dùng. Nhấn `Ctrl+C` để dừng. Không đổi host sang IP LAN hoặc public interface.

## 4. Tạo một project

1. Nhập ý tưởng, audience, genre, phong cách, ngôn ngữ, tổng thời lượng và tỷ lệ khung hình. Codex tự chọn số lượng 5–8 shot và thời lượng riêng theo nhịp câu chuyện; mỗi shot Muse tối đa 10 giây. Nếu cần dài hơn, Codex tách hành động tại các beat có ý nghĩa.
2. Chọn **Gửi Codex phân tích**. Codex chỉ tạo phương án theo schema; không có request nào gửi Muse ở bước này. Nếu Codex CLI chưa đăng nhập, badge Codex báo chưa sẵn sàng.
3. Xem logline, synopsis, Character Bible, World Bible/Prop Bible và chi tiết từng shot gồm state đầu/cuối, action beats, camera, audio, references, QA và continuity level.
4. Nếu muốn tiếp tục với phương án đó, bấm **Duyệt storyboard và tạo prompt shot đầu**. Thao tác này lưu project mới trong `projects/studio/<project-id>/`, đổi storyboard/Bible sang `APPROVED`, rồi gọi Codex với skill Muse Prompting để soạn prompt shot đầu. Prompt được lưu nguyên văn. Shot phụ thuộc chưa có prompt cho đến khi shot trước được review.

Run JSON và usage Codex lưu ở `data/studio/runs/`. Các file Bible, episode, prompt, ledger, manifest, queue, report và media nằm trong project mới. App không sửa demo hoặc Bible của project khác.

## 5. Tạo video tuần tự

1. Chọn shot kế tiếp được phép và bấm **Tạo manifest một shot**.
2. Đọc toàn bộ prompt và metadata. Mỗi manifest trong web app chứa đúng một request.
3. Điền usage basis dựa trên số request, thời lượng, tỷ lệ và references/provider usage có thể quan sát; đặt budget cap rõ ràng. Đơn vị token/credit không được gateway báo ổn định nên không tự bịa số.
4. Bấm **Duyệt usage và giới hạn**. Đây mới là ghi approval, chưa gửi video.
5. Nhập chính xác `SEND <manifest-id>` và bấm **Gửi 1 request tới Muse**. Đây là lần xác nhận gửi thật; quota có thể bị sử dụng.
6. App kiểm tra task định kỳ tối đa 30 phút. Nếu gateway lỗi, hết session, task failed, poll lỗi hoặc download/QC lỗi, app dừng, giữ nguyên task record và không submit lại. Sau `POLL_ERROR`, có thể bấm kiểm tra trạng thái lại; đó chỉ là poll, không phải retry generation.
7. Clip gốc được giữ nguyên. Nếu resolution/frame rate khác profile project, app dùng FFmpeg tạo bản conform; upscale không làm tăng chi tiết của nguồn. QC report của nguồn và bản conform được lưu trong `output/qc/`.

## 6. Continuity review và xuất

Khi clip và first/middle/last frame đã sẵn sàng:

1. Xem video trong giao diện.
2. Bấm **Gửi 3 frame cho Codex review** nếu bạn chấp nhận gửi ba ảnh tĩnh qua Codex CLI để phân tích. Video đầy đủ không được gửi cho Codex qua bước này.
3. Kiểm tra actual end state, reviewer notes và risks. Codex có thể ghi “không quan sát rõ” cho chi tiết khuất; đừng coi đó là xác nhận identity.
4. Bấm xác nhận review để ghi continuity ledger và tự tạo prompt shot kế từ last frame thực tế. Nếu đề xuất sai, không xác nhận; sửa brief/storyboard trước khi tiếp tục.
5. Lặp lại từng shot. App không chạy generation hàng loạt hoặc chạy song song các shot phụ thuộc.
6. Khi toàn bộ shot có output review và QC_PASSED, bấm **Render và QC episode**. File MP4 và báo cáo QC xuất trong `output/exports/` và `output/qc/`.

## 7. Tạo bản nháp YouTube SEO và metadata

Sau khi episode xuất thành công với QC `PASS`, mở project đã hoàn tất và dùng phần **YouTube SEO & Metadata**:

1. Dán transcript SRT/VTT đã khớp với MP4 nếu muốn tạo chapter. Có thể để trống; khi đó app bỏ qua chapter.
2. Bấm **Tạo bản nháp YouTube SEO & thumbnail**. Codex nhận các frame đầu/giữa/cuối của MP4 cuối, project profile và continuity ledger. Nó không nhận toàn bộ video hoặc nghe audio trong bước này.
3. Xem tiêu đề, description, tags, hashtag, thumbnail concepts và các ghi chú. Mở thư mục được hiển thị để xem các file đầy đủ và helper checks.
4. Nếu có chapter, đối chiếu mọi mốc với MP4. Helper chỉ kiểm tra cấu trúc/timestamp; không chứng minh nội dung chapter chính xác.

Bản nháp được lưu trong `episodes/EP001/metadata/draft-<timestamp>-<id>/`. App không đăng nhập YouTube, upload, lên lịch hoặc publish.

## 8. Trạng thái và lỗi thường gặp

| Trạng thái | Ý nghĩa | Việc cần làm |
|---|---|---|
| `ANALYZING` | Codex đang tạo package | Chờ; chưa có Muse request |
| `DRAFT_READY` | Bible/storyboard DRAFT đã sẵn sàng | Review nội dung rồi duyệt hoặc tạo run mới |
| `PLAN_APPROVED` | Storyboard đã duyệt, prompt shot đầu đã tạo | Tạo manifest cho một shot |
| `MANIFEST_DRAFT` | Request đã được đóng băng để review | Kiểm tra prompt, điền usage và cap |
| `MANIFEST_APPROVED` | Budget đã duyệt | Nhập phrase gửi thật |
| `SUBMITTED` / `RUNNING` | Muse đã nhận task | Chờ poll; không submit lại |
| `MEDIA_READY` / `QC_WARN` | Clip đã tải và xử lý | Xem video và kết quả QC |
| `REVIEW_READY` | Codex đã đưa ra continuity assessment | Xem lại rồi xác nhận hoặc dừng |
| `REVIEWED` | Ledger đã ghi; prompt shot sau có thể sẵn sàng | Tạo manifest shot kế hoặc render khi đủ shot |
| `FAILED` | Codex/provider/generation dừng | Đọc lỗi và queue; request mới cần manifest/approval riêng |
| `POLL_ERROR` | Không lấy được trạng thái task | Kiểm tra kết nối rồi poll lại; không có generation request mới |

Nếu badge Muse gateway chưa kết nối: kiểm tra Docker, bearer key trong đúng terminal, và `projects/studio/<id>/project.yaml` vẫn trỏ tới loopback. Nếu Codex chưa sẵn sàng: kiểm tra `codex --version`, `codex login` và `ANISTUDIO_CODEX_EXE` nếu cần. Không đưa key/cookie vào brief hoặc chat.

## 9. Phạm vi và giới hạn

- Codex CLI dùng tài khoản/usage Codex hiện có; brief và ảnh continuity bạn chủ động gửi sẽ được đưa cho Codex để xử lý.
- Muse2API là gateway thử nghiệm không chính thức. Một smoke request đã thành công trên tài khoản hiện tại; điều đó không bảo đảm request khác, duration khác, reference adherence hoặc batch reliability.
- UI không hỗ trợ upload reference assets trong phiên bản đầu; Codex không được phép tự bịa đường dẫn ảnh.
- Một request lỗi không được tự retry. Muốn thử lại phải đọc kết quả, tạo manifest mới và duyệt usage/budget lại.
- UI local hiện điều phối story/prompt/generation/media/QC/export; không tự động publish hoặc upload video ra dịch vụ khác.
- YouTube metadata chỉ chạy sau export QC `PASS`. Lint score dùng heuristic tiếng Anh, không phải đánh giá chất lượng tiếng Việt hay dự đoán hiệu quả. Khung hình đại diện không chứng minh được chuyển động hoặc nội dung audio.
