# Third-party Skills — cách bổ sung an toàn

## Nguồn tham khảo
1. Drama Skills — https://github.com/zenstory-ai/drama-skills
2. Muse Video Prompt Skill — https://github.com/masonmosen/muse-video-prompt-skill
3. Universal Video Skills — https://github.com/svenkatreddy/universal-video-skills

## Cách dùng

### Drama Skills
README upstream nêu lệnh cài project-local:

```powershell
npx skills add zenstory-ai/drama-skills -y
```

Không dùng `-g` nếu không muốn cài global. Sau lệnh, kiểm tra `.agents/skills/` và xem các Skills được thêm. Giữ repo upstream riêng hoặc ghi commit/tag đã dùng.

### Muse Video Prompt Skill
Clone vào thư mục tạm để đọc `SKILL.md`, `references/`, scripts và LICENSE. Nếu muốn dùng trong Codex, đưa nguyên cấu trúc Skill vào `.agents/skills/muse-video-prompt-skill/`. Không tự động dùng provider-specific tool call nếu hệ thống của bạn không có tool đó; thay bằng Muse2API adapter sau khi kiểm chứng.

### Universal Video Skills
Clone và audit cây `skills/`, `docs/`, `examples/`, `scripts/`. Chỉ import Skill về cinematography/prompt craft/QA thực sự cần. Tránh cài trùng chức năng với Drama Skills.

## Checklist trước khi import
- [ ] Đọc LICENSE và attribution.
- [ ] Đọc toàn bộ SKILL.md cùng references.
- [ ] Kiểm tra scripts có chạy shell, tải file, đọc env hoặc gửi dữ liệu ra ngoài không.
- [ ] Kiểm tra phụ thuộc Node/Python và phiên bản.
- [ ] Kiểm tra Skill dùng tool/API cụ thể nào.
- [ ] Kiểm tra có yêu cầu model/provider ngoài ý muốn không.
- [ ] Ghi lại commit SHA/tag để tái lập.
- [ ] Chạy thử bằng tác vụ chỉ lập kế hoạch, chưa tạo media.

Không copy nội dung repo thứ ba vào bộ starter nếu chưa cần; ưu tiên cài upstream để nhận cập nhật và giữ attribution.

## Kết quả audit repository (2026-11-16)

Các repo được clone nông và đọc tĩnh trong thư mục tạm, không cài, không chạy script. SHA ghi nhận để tái lập audit; do thư mục upstream thay đổi, cần audit lại trước khi import.

| Repository | SHA đã xem | License | Phạm vi / tác động |
|---|---|---|---|
| `zenstory-ai/drama-skills` | `37232f6d22e174c36e321d2e3a1a3ae871e7d602` | MIT | 13 entrypoint SKILL.md trong checkout, các workflow viết kịch bản, asset, storyboard, prompt, production, edit và review; có nhiều script Python/project tools. Phạm vi bao phủ rộng và trùng lặp với CLI, schema và continuity engine của repo này. |
| `masonmosen/muse-video-prompt-skill` | `0885b51e9b96da786939882751d929c186e9378b` | MIT | Một SKILL.md, các tài liệu prompt/continuity/stitch và script trích frame. Tập trung vào Muse web, dùng các chi tiết capability theo workflow của tác giả; chưa xác minh trên tài khoản hiện tại. |
| `svenkatreddy/universal-video-skills` | `0c384d395290eaebf416e4bcfc4a7bb19b20aaac` | MIT | Tám SKILL.md về story/shots, character, cinematography, prompt, model adapters, assembly và QA; có script Python/Node/shell và adapter notes cho nhiều provider. Phạm vi rộng, chồng lấn với hai repo kia. |

### Lựa chọn ban đầu cho MVP (2026-11-16)

- Không import cả ba repo vào MVP: chưa cần cài phụ thuộc bên ngoài, tránh hai bộ quy tắc chỉ đạo workflow cạnh tranh nhau, và giữ một schema/source-of-truth của dự án.
- Tạo skill project-local `anistudio-story-continuity` chỉ cho workflow đã chọn: script/bible/storyboard/prompt/ledger và cổng approval. Skill không tự gọi provider.
- Có thể xem xét một SKILL cụ thể từ Drama Skills hoặc Muse Prompt trong tương lai. Trước khi import phải đọc toàn bộ SKILL.md, references và script được dẫn; kiểm dependency/API/security; giữ LICENSE và attribution. Audit lần này chưa là bước xét duyệt import.

## Triển khai chọn lọc trong repo (2026-11-17)

Theo yêu cầu mở rộng, các kỹ thuật phù hợp từ cả ba nguồn đã được triển khai thành ba skill project-local viết lại cho schema và cổng duyệt của repo. Đây **không phải** thao tác cài nguyên gói upstream. Các revision bên dưới được giữ cố định để truy nguồn; tại revision đã audit, ba repo khai báo MIT. Tệp gốc, script, asset, API adapter và browser workflow không được chép hoặc chạy.

| Nguồn đã pin | Skill nội bộ | Nội dung được đưa vào | Phần loại trừ |
|---|---|---|---|
| `zenstory-ai/drama-skills` — `37232f6d22e174c36e321d2e3a1a3ae871e7d602` | `.agents/skills/anistudio-drama-workbench/` | Dramatic beat coverage, shot purpose, start/action/end, blocking/screen direction, timing, bibles và rà soát shot phụ thuộc; tham khảo `short-drama-storyboard` và `short-drama-video-prompts`. | Schema Markdown riêng của upstream, các script/checker và quy trình nhiều file riêng không tương thích với YAML/Pydantic hiện tại. |
| `masonmosen/muse-video-prompt-skill` — `0885b51e9b96da786939882751d929c186e9378b` | `.agents/skills/anistudio-muse-prompting/` | Prompt có cấu trúc từ format/subject/scene/action/camera/audio tới references/constraints; prompt chính xác, kiểm năng lực, handoff tuần tự và hậu kiểm. | Tool `media.generate_video`, snapshot ID, giới hạn 10 giây, mặc định tiếng thoại và script `extract_frames.py`; không có bằng chứng những hành vi này áp dụng cho adapter/account của repo. |
| `svenkatreddy/universal-video-skills` — `0c384d395290eaebf416e4bcfc4a7bb19b20aaac` | `.agents/skills/anistudio-cinematic-qa/` | Camera size/angle/movement, ánh sáng có nguồn, review có frame/time/report evidence, kiểm đoạn cuối và điểm nối; kết hợp chọn lọc `cinematic-direction` và `video-qa`. | Adapter cho model khác, identity-embedding scripts, workflow Google Flow/Veo, shell/npm scripts và verdict tự động. |

### Tích hợp và kiểm soát

- `.agents/skills/README.md` là danh mục và bảng định tuyến; `anistudio-story-continuity` vẫn là skill router dùng chung.
- Router hiện được nhúng vào project context của Codex web qua `project_authoring_context()`. Các nguyên tắc cốt lõi cũng được ghi trong router để các lượt structured prompt cô lập không phụ thuộc việc chúng có thể đọc các thư mục skill khác hay không.
- Skills chuyên biệt tham chiếu `Shot`, `ShotState`, `ActionBeat`, `CameraSpec`, `ReferenceSpec`, `WorldBible`, provider config, QC report và Continuity Ledger hiện có; không tạo nguồn dữ liệu sáng tạo thứ hai.
- Các skills chỉ hướng dẫn lập kế hoạch/review. Storyboard, budget, request gửi Muse, ghi ledger và export tiếp tục theo trạng thái/cổng duyệt của project. Không hardcode capability snapshot hoặc duration chưa được xác minh.
- Tài liệu này ghi nhận việc audit và ánh xạ nguồn; `SKILL.md` nội bộ chứa nội dung viết lại và liên kết source/license theo commit. Không bundle upstream code hoặc LICENSE file vì không copy file/code upstream.

### Trạng thái xác minh

Đã đọc ở revision đã pin: hai entrypoint Drama (`short-drama-storyboard`, `short-drama-video-prompts`) và references shot-craft/video-prompt; Muse entrypoint, prompt-template, stitch-workflow, model-notes và script trích frame; Universal entrypoint cinematic-direction/video-qa cùng camera, lighting, QA và frame-evidence references. Đã đối chiếu LICENSE của cả ba repo. Chỉ áp dụng nội dung phù hợp; mọi giới hạn capability vẫn theo tài liệu/probe của provider trong project.

### Bằng chứng kiểm tra tại checkout

- `uv run python scripts/validate_skills.py` — thành công: 4 skill project-local có frontmatter YAML, tên thư mục/tên skill duy nhất và các link Markdown nội bộ hợp lệ.
- `uv run pytest -q` — **38 passed**. Đây là suite hiện có của ứng dụng; nó không đo chất lượng nội dung sáng tạo hoặc chứng minh provider tuân thủ prompt.
- Không gửi Muse generation request trong đợt mở rộng skills này. Việc triển khai skill không phải bằng chứng rằng Muse nhận prompt tốt hơn hoặc nội dung hình ảnh đã tự động đạt; end-to-end vẫn cần request được duyệt và review clip thật.
