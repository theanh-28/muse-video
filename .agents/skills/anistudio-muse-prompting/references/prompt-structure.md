# Prompt structure and provider boundaries

The project's `build_shot_prompt` maps existing story data into provider-facing text. Keep content anchored to the approved `Shot` and preserve the exact text that is ultimately sent.

| Prompt concern | Project source |
|---|---|
| Duration and aspect ratio | `Shot.planned_duration_seconds`, `Episode.aspect_ratio`, approved manifest |
| Subject identity and invariant locks | `CharacterBible`, `Shot.continuity_locks`, approved reference assets |
| Location, set, prop, time, weather, palette | `WorldBible`, `ShotState`, `PropBible` |
| Opening pose and geography | `Shot.start_state`; actual prior end state when a dependency was reviewed |
| Action and timing | Ordered `Shot.action_beats`; only use time ranges when they describe a valid, non-conflicting sequence |
| Endpoint and camera | `Shot.end_state`, `CameraSpec`, lighting fields |
| Dialogue, voice, effects, music | `AudioSpec`; do not invent unscripted dialogue |
| References and exclusions | Existing `ReferenceSpec` files, reference plan, negative constraints |
| Review targets | Observable `Shot.qa_checks` |

## Confirmed vs. unknown behavior

- Read `ProviderSettings` and the configured provider adapter. A static field such as `supports_image_reference=True` describes what the adapter advertises; it does not alone verify that a specific account/task honored the reference.
- `max_duration_seconds=None` means no documented maximum is known in this config. Do not replace it with a remembered 10-second rule.
- The audited Muse2API schema had no `snapshot_id` / `resume_from_snapshot_id` continuation field. Use a new request with an image reference only when the adapter and current gateway accept it; label continuity as image-reference or prompt-only.
- Keep references within the configured and observed provider limits. Confirm each file exists, is project-relative, has the declared media type, and is allowed to be sent.
- Aspect ratio and resolution in prompts/requests do not prove output dimensions. Use ffprobe and project QC on the result.

## When the shot is too complex

Recommend simplifying the single shot, splitting it into separate sequential shots, or choosing a cut that tolerates a state change. Do not mutate an approved storyboard or create dependent prompts from assumed media. Any revised shot still needs its own reviewed manifest and approvals.

## Attribution

Prompt organization and post-generation review are adapted from the pinned upstream skill's prompt-template and stitch-workflow references, rewritten for this repository's fields and provider limitations. See source and MIT license links in the adjacent `SKILL.md`.
