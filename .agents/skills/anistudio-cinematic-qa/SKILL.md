---
name: anistudio-cinematic-qa
description: "Plan purposeful camera/light choices or review generated animation with written frame, continuity, and technical evidence. Use for cinematography, shot QC, edit joins, and media review; do not treat visual review as proof of audio or motion quality."
---

# Anistudio Cinematic Direction and QA

This skill combines model-neutral camera/light planning with evidence-based review. Follow the project's approved style and continuity locks. Technical checks, frame observations, motion review, and audio review are separate evidence claims.

## Camera and lighting during planning

1. Choose framing (`CameraSpec.shot_size`) for the information the audience needs: orientation, action, expression, or a meaningful prop.
2. Choose a viewing angle (`CameraSpec.angle`) and screen direction that make the geography readable.
3. Choose one primary movement (`CameraSpec.movement`) and motivate it by the beat. Specify the start/landing when helpful; use a fixed camera when stillness serves the shot.
4. Use `lens_look` and `focus` only when perspective or depth of field matters. They are prompt cues, not guaranteed optical controls.
5. Describe a motivated light source, its direction and quality, time of day, and palette in the shot and World Bible. Keep a stable project-wide look unless an explicit story event justifies a change.
6. Keep screen-space composition, action complexity, and subject count legible for the selected aspect ratio. Do not overload one shot with unrelated moves or light changes.

## Evidence-based media review

1. Read the approved shot purpose, start/end states, action beats, character/costume/prop locks, camera/light plan, QA checks, and previous ledger entry.
2. Check technical evidence separately: decode, streams, duration, size/FPS, and black-frame or other reported QC checks. Cite the report or command result; do not assume a successful download means visual quality passed.
3. Inspect first, middle, last, beat, and join frames where available. Pay close attention to the final portion of each clip and both sides of a cut.
4. Compare observed people, costume, props, geography, screen direction, camera, lighting, and story action against the approved plan. Record concrete evidence and note when a detail is obscured or too small to verify.
5. For motion defects such as warping, foot sliding, or incomplete action, inspect the moving video; still frames alone cannot establish motion quality. For audio, listen to the audio; video/frame inspection cannot establish dialogue intelligibility, sync, or mix quality.
6. Separate observation from inference. Say which frame/time/report supports a claim; mark uninspected properties `not checked` or `not clearly visible`.
7. Write a concise result: passed checks, defects and evidence, risks, unresolved human review, and a recommendation to accept, revise, or cut. Do not change job status, Continuity Ledger, or approved story files without the workflow's explicit confirmation.

## Correction discipline

- Map each defect to the smallest specific fix. When suggesting a new attempt, name one prompt or shot variable to change and why.
- Repeated failures may mean the shot is too complex; propose a simpler action, a new cut, or a storyboard replan.
- Never trigger an automatic retry or mark a clip accepted merely because a correction seems likely to work.

See [cinematic and evidence checklist](references/cinematic-and-evidence-checklist.md) for a short review worksheet.

## Source adaptation

This local skill is independently rewritten, selectively informed by `cinematic-direction` and `video-qa` from [svenkatreddy/universal-video-skills at 0c384d395290eaebf416e4bcfc4a7bb19b20aaac](https://github.com/svenkatreddy/universal-video-skills/tree/0c384d395290eaebf416e4bcfc4a7bb19b20aaac). Upstream license: [MIT](https://github.com/svenkatreddy/universal-video-skills/blob/0c384d395290eaebf416e4bcfc4a7bb19b20aaac/LICENSE). No upstream scripts, provider adapters, or browser workflows are bundled.
