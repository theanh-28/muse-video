# Shot design checklist

Use this checklist while authoring the project's `Episode` and `Shot` models.

## Dramatic coverage

- Does each shot have a distinct purpose that changes what viewers know, feel, or expect?
- Are the key decisions, reversals, reveals, and reactions visible in the planned coverage?
- Does every supplied story beat have a shot or a documented reason to omit it?
- Does the ending resolve the episode's main promise or deliberately leave a stated hook?

## Blocking and screen direction

- Can a reader tell where each character is relative to the room, landmarks, other characters, and important props?
- Are screen-left/right and character-left/right distinguished when handoffs matter?
- Are entrances, exits, prop transfers, eyelines, and axis changes described in the shot states or action beats?
- For a vertical frame or group shot, is depth used to keep roles readable rather than placing everyone in a flat row?

## Action and timing

- Does the shot begin from one concrete visible state and end at another?
- Are beats ordered by cause and effect, with observable actions rather than internal-only intentions?
- Can the selected action fit the planned duration? Simplify or split overloaded beats; do not add arbitrary micro-timing.
- If dialogue or narration is specified, does the planned duration leave room for the words and the listener's reaction?

## Camera and visual locks

- Does framing reveal the story information needed in this shot?
- Is the camera movement intentional and motivated, with a clear path/landing when applicable?
- Are location, light direction, time, weather, costume, prop state, and screen geography consistent with approved locks?
- Are QA checks observable in the generated media rather than vague goals such as “make it cinematic”?

## Revision handoff

- Keep existing IDs for local adjustments; use a new ID only for a genuinely new shot.
- List every dependent shot whose start state, prop ownership, geography, camera axis, or prompt may now be stale.
- Keep intended state in the storyboard. Record actual state in the Continuity Ledger only after reviewing media.

## Attribution

Adapted from shot-craft and blocking concepts in `short-drama-storyboard` at the pinned MIT source revision linked in the adjacent `SKILL.md`. The checklist is rewritten for this repository and its `ShotState`, `ActionBeat`, and `CameraSpec` fields.
