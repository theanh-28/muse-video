# Cinematic and evidence checklist

## Before generation

- [ ] Shot size, angle, movement, and screen direction are all clear.
- [ ] Camera movement has one primary path and a story reason.
- [ ] Lighting names a source/direction/quality, and agrees with the World Bible.
- [ ] Style and color choices are concise and consistent across the episode.
- [ ] Composition fits the aspect ratio and makes the action/prop readable.

## After generation

| Area | Evidence to inspect | Example result |
|---|---|---|
| Story | Clip purpose and timed action beats | Purpose achieved / beat missing |
| Identity and locks | Visible character, costume, marks, props | Match / mismatch / cannot verify |
| Frame | Composition, camera, light, geography | Matches plan / specific deviation |
| Motion | Whole clip, especially action landing and tail | Complete / warped / not reviewed |
| Join | Previous last frame and current opening frame | Direction/state preserved / cut risk |
| Audio | Listen to actual rendered audio | Intelligible / mismatch / not checked |
| Technical | Saved ffprobe and FFmpeg QC reports | Values and check results; no visual inference |

Record each finding with a frame/time or report field when possible. A screenshot is evidence only for what is visible in that image. It cannot certify motion, sound, or unseen parts of the clip.

## Attribution

Camera/light and written frame-evidence QA concepts are adapted from the pinned `cinematic-direction` and `video-qa` skills. This worksheet is rewritten for this project's `CameraSpec`, QC reports, and Continuity Ledger. See the adjacent `SKILL.md` for source and MIT license links.
