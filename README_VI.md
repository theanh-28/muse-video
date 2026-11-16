# Muse Animation Studio — MVP cho Codex

Pipeline Python cho Codex quản lý kịch bản, Character Bible, storyboard, prompt và continuity; Muse/provider chỉ tạo media khi được bật và duyệt; FFmpeg/ffprobe kiểm tra, ghép và xuất video.

MVP hiện dùng `ManualProvider` mặc định. Adapter Muse2API là thử nghiệm, bị khóa gửi mặc định; quyền truy cập tài khoản Muse và tương thích gateway chưa được xác minh. Không có video nào được tạo trong lần triển khai này.

## Cài đặt

Yêu cầu Python 3.11+, `uv`, FFmpeg và ffprobe.

```powershell
uv sync --extra http --extra test
uv run python -m animation_studio.cli.main --help
```

Trên máy hiện tại, gọi CLI qua `python -m animation_studio.cli.main` vì Windows Application Control chặn launcher `anistudio.exe`.

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

`generation plan` chỉ ghi manifest `DRAFT`, không gửi request. Manifest phải có usage estimate và giới hạn ngân sách được duyệt trước khi submit; CLI yêu cầu xác nhận lần nữa tại thời điểm submit. Shot nối tiếp chỉ được prompt/lập kế hoạch sau khi clip trước được kiểm tra và ledger ghi lại end state thực tế cùng first/middle/last frame.

Sau khi media được tạo hoặc nhập thủ công:

```powershell
uv run python -m animation_studio.cli.main media inspect path\to\clip.mp4 --project-dir projects/my-show --frames-dir episodes/EP001/frames/SHOT_001
uv run python -m animation_studio.cli.main continuity update projects/my-show/episodes/EP001/episode.yaml --shot-id SHOT_001 --actual-end-state path\to\observed-end-state.yaml --frames-dir episodes/EP001/frames/SHOT_001
```

Tạo cut list từ `templates/cut-list.yaml`, rồi render/QC:

```powershell
uv run python -m animation_studio.cli.main episode render path\to\cut-list.yaml --project-dir projects/my-show
uv run python -m animation_studio.cli.main episode qc projects/my-show/final/episode.mp4 --project-dir projects/my-show
```

## Skills và provider

- Skill dự án: `.agents/skills/anistudio-story-continuity/` — quy tắc viết, prompt và cập nhật continuity theo dữ liệu trên đĩa.
- Không cài các Skills bên thứ ba đã audit vì phạm vi trùng lặp rộng; xem `docs/THIRD_PARTY_SKILLS.md`.
- Quyết định provider và continuity: `docs/ADR/0001-provider-integration.md`, `docs/ADR/0002-continuity-strategy.md`.
- Trạng thái kiểm chứng, rủi ro và giới hạn: `docs/IMPLEMENTATION_PLAN.md`, `docs/RESEARCH_NOTES.md`.
- Không lưu cookie, session hoặc API key trong repo. Muse2API chỉ đọc bearer key từ biến môi trường khi người dùng tự cấu hình provider.

## Kiểm tra

```powershell
uv run pytest -q
```

Các test adapter dùng HTTP mock; chúng không chứng minh gateway hoặc tài khoản Muse hoạt động. Test media dùng fixture cục bộ tổng hợp, không phải video do Muse tạo.
