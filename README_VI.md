# Muse Animation Studio — MVP cho Codex

Pipeline Python cho Codex quản lý kịch bản, Character Bible, storyboard, prompt và continuity; Muse/provider chỉ tạo media khi được bật và duyệt; FFmpeg/ffprobe kiểm tra, ghép và xuất video.

Template dự án mặc định dùng `ManualProvider`; demo hiện tại dùng adapter Muse2API thử nghiệm. Một request chẩn đoán 6 giây đã tạo được video thật trên tài khoản hiện tại. Điều này chỉ xác minh một request, không bảo đảm quota hoặc batch production. Giao diện web local mới dùng Codex CLI để lập DRAFT, rồi yêu cầu duyệt storyboard, usage/budget và xác nhận riêng trước mỗi request video.

## Cài đặt

Yêu cầu Python 3.11+, `uv`, FFmpeg và ffprobe.

```powershell
uv sync --extra http --extra test
uv run python -m animation_studio.cli.main --help
```

Trên máy hiện tại, gọi CLI qua `python -m animation_studio.cli.main` vì Windows Application Control chặn launcher `anistudio.exe`.

## Dùng giao diện web

Giao diện chạy riêng trên máy này tại `http://127.0.0.1:8765`; chưa cần trình duyệt cloud hoặc tài khoản web riêng. Cần Codex CLI đã cài và đăng nhập, Docker/Muse2API, cùng FFmpeg/ffprobe.

1. Terminal PowerShell thứ nhất khởi động gateway:

   ```powershell
   Set-Location D:\muse2api-runtime
   docker compose up -d --build
   ```

2. Terminal PowerShell thứ hai tại repo cài web extra, nạp bearer key vào đúng process và mở app:

   ```powershell
   Set-Location D:\muse-animation-studio-starter
   uv sync --extra web

   $keyLine = Get-Content -Encoding utf8 'D:\muse2api-runtime\.env' |
     Where-Object { $_.StartsWith('MUSE2API_KEY=') }
   if (-not $keyLine) { throw 'Không tìm thấy MUSE2API_KEY trong .env' }
   $env:MUSE2API_API_KEY = $keyLine.Substring('MUSE2API_KEY='.Length)

   uv run python -m animation_studio.cli.main web --open-browser
   ```

3. Nhập brief và cài đặt tập trong form. Codex tạo Bible và storyboard **DRAFT** để bạn xem chi tiết; bước này không gọi Muse. Duyệt storyboard trong giao diện để lưu project, chuyển status và tạo prompt shot đầu.
4. Chọn một shot, tạo manifest rồi kiểm tra prompt, provider, duration, aspect ratio và references. Nhập cơ sở usage cùng giới hạn tối đa; duyệt budget. Để gửi video, nhập đúng cụm `SEND <manifest-id>` và bấm nút xác nhận. Mỗi lần chỉ gửi một request.
5. Giao diện tự poll task tối đa 30 phút, tải media, trích frame, kiểm tra bằng ffprobe/FFmpeg, conform theo profile project và chạy QC. Lỗi dừng quy trình; không có retry generation tự động.
6. Bấm **Gửi 3 frame cho Codex review** nếu muốn Codex phân tích continuity. Ba frame tĩnh sẽ được gửi qua Codex CLI; xem lại đề xuất và xác nhận trước khi ledger thay đổi. Khi chấp nhận, app ghi actual end state và tạo prompt shot kế tiếp từ last frame thực tế.
7. Sau khi mọi shot đều được review và QC_PASSED, dùng **Render và QC episode** để xuất MP4.

Run và brief lưu tại `data/studio/runs/`; project mới lưu tại `projects/studio/`. Server chỉ bind `127.0.0.1`. Codex CLI dùng đăng nhập Codex hiện có; khóa Muse không được đưa vào tiến trình Codex. Xem [Hướng dẫn giao diện web](docs/USER_GUIDE_WEB.md) để hiểu các trạng thái và xử lý lỗi.

## Tạo dự án và tập

```powershell
uv run python -m animation_studio.cli.main project init projects/my-show --title "Tên dự án"
uv run python -m animation_studio.cli.main episode init EP001 --project-dir projects/my-show --title "Tập đầu"
```

Sửa các file Bible và storyboard trong thư mục dự án. Mọi nội dung mới bắt đầu ở `DRAFT`; không coi storyboard dự kiến là quan sát từ clip thực tế.

## Luồng sản xuất

```powershell
uv run python -m animation_studio.cli.main storyboard validate projects/my-show/episodes/EP001/episode.yaml
uv run python -m animation_studio.cli.main prompts build projects/my-show/episodes/EP001/episode.yaml --shot-id SHOT_001
uv run python -m animation_studio.cli.main generation plan projects/my-show/episodes/EP001/episode.yaml --shot-id SHOT_001
```

`generation plan` chỉ ghi manifest `DRAFT`, không gửi request. Manifest phải có usage estimate và giới hạn ngân sách được duyệt trước khi submit; CLI yêu cầu xác nhận lần nữa tại thời điểm submit. Nếu bất kỳ request nào trong manifest chưa qua continuity gate, CLI từ chối toàn bộ manifest trước khi gửi request; hãy lập và duyệt manifest mới sau khi shot tiền nhiệm được review. Shot nối tiếp chỉ được prompt/lập kế hoạch sau khi clip trước được kiểm tra và ledger ghi lại end state thực tế cùng first/middle/last frame.

Sau khi media được tạo hoặc nhập thủ công:

```powershell
uv run python -m animation_studio.cli.main generation import-media projects/my-show/episodes/EP001/generation/jobs.json --shot-id SHOT_001 --media-file path\to\clip.mp4 --provider-model "Muse Video v1"
uv run python -m animation_studio.cli.main media inspect path\to\clip.mp4 --project-dir projects/my-show --frames-dir episodes/EP001/frames/SHOT_001
uv run python -m animation_studio.cli.main continuity update projects/my-show/episodes/EP001/episode.yaml --shot-id SHOT_001 --actual-end-state path\to\observed-end-state.yaml --frames-dir episodes/EP001/frames/SHOT_001
```

`generation import-media` chỉ nhận job `ManualProvider` đang chờ media. Lệnh kiểm tra clip bằng ffprobe, sao chép nó vào `episodes/EP001/clips/SHOT_001/`, không ghi đè file, rồi lưu output path, hash SHA-256, metadata media, model (nếu cung cấp) và thời điểm nhập vào job queue. Import không tự đánh dấu continuity đã review. Sau khi kiểm tra clip, `continuity update` ghi trạng thái quan sát vào ledger và chuyển job tương ứng từ `generated` sang `reviewed`.

Với Muse2API thử nghiệm đã được bật, `generation status ... --refresh` poll task một lần và tải kết quả đã hoàn tất vào thư mục clips theo shot. CLI kiểm tra file tải về bằng ffprobe trước khi đánh dấu job `generated`; lỗi được lưu trong queue và không gửi lại generation request. Nếu file theo task ID đã tồn tại từ lần tải trước, CLI kiểm tra lại file đó và không ghi đè.

Tạo cut list từ `templates/cut-list.yaml`, rồi render/QC:

```powershell
uv run python -m animation_studio.cli.main episode render path\to\cut-list.yaml --project-dir projects/my-show
uv run python -m animation_studio.cli.main episode qc projects/my-show/final/episode.mp4 --project-dir projects/my-show
```

## Skills và provider

- Skill router: `.agents/skills/anistudio-story-continuity/` — source of truth, continuity và cổng duyệt.
- Ba skill chuyên biệt: `anistudio-drama-workbench` (story/bible/storyboard), `anistudio-muse-prompting` (prompt một shot theo capability hiện có), `anistudio-cinematic-qa` (camera/ánh sáng và QA dựa trên evidence).
- Bốn skill metadata YouTube: `yt-package`, `yt-thumbnail`, `yt-seo`, `yt-chapters`; chỉ dùng sau khi có video thực tế. Bản tích hợp có helper và license MIT đã audit, không có đăng nhập, upload hoặc thao tác tài khoản YouTube.
- Xem `.agents/skills/README.md`, `docs/THIRD_PARTY_SKILLS.md` và `docs/YOUTUBE_METADATA_WORKFLOW.md` để biết routing, nguồn, giới hạn và cách tạo metadata theo tập.
- Quyết định provider và continuity: `docs/ADR/0001-provider-integration.md`, `docs/ADR/0002-continuity-strategy.md`.
- Trạng thái kiểm chứng, rủi ro và giới hạn: `docs/IMPLEMENTATION_PLAN.md`, `docs/RESEARCH_NOTES.md`.
- Không lưu cookie, session hoặc API key trong repo. Muse2API chỉ đọc bearer key từ biến môi trường khi người dùng tự cấu hình provider.

## Kiểm tra

```powershell
uv run python scripts/validate_skills.py
uv run pytest -q
```

Các test adapter dùng HTTP mock; chúng không chứng minh gateway hoặc tài khoản Muse hoạt động. Test media dùng fixture cục bộ tổng hợp, không phải video do Muse tạo.

Trạng thái triển khai, video smoke test thật và giới hạn provider: [docs/MUSE2API_DEPLOYMENT.md](docs/MUSE2API_DEPLOYMENT.md). Kiến trúc web và quy trình Codex: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
