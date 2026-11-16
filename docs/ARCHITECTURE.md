# Kiến trúc đề xuất

## Mục tiêu
Tạo pipeline sản xuất phim hoạt hình nhiều shot. Codex làm đạo diễn/điều phối; Muse sinh clip; FFmpeg hậu kỳ. MVP ưu tiên CLI và thư mục dự án trên ổ đĩa, chưa cần dashboard.

## Thành phần

```text
User brief
   |
   v
Codex + Agent Skills
   |-- script / story structure
   |-- character & world bibles
   |-- storyboard / shot list
   |-- prompt package
   |-- continuity decisions
   v
Project files (source of truth)
   |
   v
Orchestrator (Python CLI; later optional API)
   |-- validate shot dependencies
   |-- require approval before generation
   |-- submit/poll/download via VideoProvider
   |-- persist task IDs and usage observations
   v
MuseProvider interface
   |-- Muse2API adapter (experimental, only after audit)
   |-- Manual provider (prompt package + user places output files)
   v
Downloaded clip + ffprobe + extracted frames
   |
   v
Continuity review and ledger update
   |
   v
FFmpeg assembly → MP4 + QC report
```

## Không làm trong MVP
- Không xây dashboard React trước khi CLI workflow chạy ổn.
- Không dùng Remotion để giả lập hoạt động nhân vật.
- Không thêm Blender/Godot/Three.js nếu shot được sinh trực tiếp bằng Muse.
- Không tự động upload YouTube.
- Không chạy hàng loạt hoặc song song các shot phụ thuộc continuity.

## Stack khởi đầu
- Python 3.11+; dùng `uv` quản lý môi trường.
- Pydantic cho model dữ liệu; PyYAML cho config; Typer cho CLI; httpx chỉ khi cần HTTP adapter.
- FFmpeg + ffprobe cài ngoài Python và phải có trên PATH.
- Lưu metadata dạng JSON/YAML/Markdown theo từng episode; media lưu dạng file.
- Có thể thêm FastAPI/SQLite/PostgreSQL khi cần service/dashboard; không bắt buộc cho MVP.

## Provider boundary
Định nghĩa interface nội bộ với các hành động: `capabilities()`, `submit_video(request)`, `get_task(task_id)`, `download_result(task_id, destination)`. Không hardcode API chưa kiểm chứng. Adapter phải báo rõ capability nào được hỗ trợ và nguồn bằng chứng.
