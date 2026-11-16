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

### Lựa chọn cho MVP

- Không import cả ba repo vào MVP: chưa cần cài phụ thuộc bên ngoài, tránh hai bộ quy tắc chỉ đạo workflow cạnh tranh nhau, và giữ một schema/source-of-truth của dự án.
- Tạo skill project-local `anistudio-story-continuity` chỉ cho workflow đã chọn: script/bible/storyboard/prompt/ledger và cổng approval. Skill không tự gọi provider.
- Có thể xem xét một SKILL cụ thể từ Drama Skills hoặc Muse Prompt trong tương lai. Trước khi import phải đọc toàn bộ SKILL.md, references và script được dẫn; kiểm dependency/API/security; giữ LICENSE và attribution. Audit lần này chưa là bước xét duyệt import.
