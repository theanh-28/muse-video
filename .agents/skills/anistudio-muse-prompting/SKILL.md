---
name: anistudio-muse-prompting
description: "Write or review provider-facing prompts for an approved animation shot using the current Muse gateway capability evidence. Use for shot prompt preparation, reference planning, and one-shot manifest review; never submits generation by itself."
---

# Anistudio Muse Prompting

Use this skill only after the shot and its source-of-truth locks are approved. It prepares one shot request at a time; it does not authorize or submit generation.

## Capability preflight

1. Read the project's provider configuration and `docs/RESEARCH_NOTES.md`. Check the current adapter/gateway evidence for each requested field: duration, aspect ratio, image/video/audio references, and continuation.
2. Treat `null`, absent, or unprobed capability values as unknown. A field accepted by an adapter or seen in upstream code is not proof the current account/model supports it.
3. Do not carry over the upstream Muse skill's 10-second limit, snapshot continuation ID, voice defaults, or filename behavior as platform guarantees. This project's Muse2API request contract has no verified native snapshot continuation; inspect the current configuration instead of inferring support.
4. If a requested feature is unsupported or unknown, explain the limitation and prepare a truthful alternative (separate shot, confirmed image reference, edit cut, or prompt-only continuity with risk recorded).

## One-shot prompt workflow

1. Read the approved `Shot`, current Character/World/Prop Bible, and actual Continuity Ledger observations for its dependencies.
2. Build the prompt from the approved shot data. Preserve the planned duration, story purpose, opening/end state, action order, dialogue, camera intent, visual style, and negative constraints. Do not add a new character, prop, line of dialogue, or action.
3. Organize the language so the model can distinguish: output format/duration, visible subjects and locks, location/light/style, starting pose, chronological action, ending pose, camera, audio, ordered references, and constraints. Keep only details that help this shot; avoid contradictory or repeated instructions.
4. Convert abstract intent to visible behavior. State the action's trigger, direction, contact point, and resulting state when relevant. Avoid impossible precision, multiple competing camera moves, and asking the model to repeat an action already completed in the previous shot.
5. For a reference, point to an existing project file and record its role, order, and the facts it governs. A previous last frame may align the next shot only after the previous clip is actually reviewed and the frame is saved in the ledger. Never claim it guarantees identity or seamless continuation.
6. Review the exact provider-facing text and one-shot manifest, including provider, duration, aspect ratio, reference count, and evidence-based usage cap. Once approved, preserve the exact prompt in the generation record.

## Shot N+1 handoff

- For dependent shots, wait until shot N's output is inspected. Use its actual observed end state and approved last frame, not its planned `end_state`.
- If the actual clip differs from the storyboard, state the difference and ask for the appropriate replan before preparing a dependent prompt.
- Keep one manifest/request per shot and follow all current project approval gates. Polling an existing task is not permission to resubmit it.
- The upstream Muse Video skill describes a separate built-in tool and snapshot workflow. This repo's Muse2API adapter does not provide that tool contract; do not copy its API calls or assert its behavior here.

## Output and limits

- Use `prompts build` or the web studio's one-shot manifest flow to save the actual prompt. Review the resulting text before any send approval.
- A prompt is a specification, not evidence that a provider obeyed it. Generated output must be inspected and recorded separately.
- This skill neither grants a usage estimate nor a budget approval, and it cannot send or retry generation.

See [prompt structure and provider boundaries](references/prompt-structure.md) for the field mapping and safe fallback rules.

## Source adaptation

This local workflow is independently rewritten and selectively informed by [masonmosen/muse-video-prompt-skill at 0885b51e9b96da786939882751d929c186e9378b](https://github.com/masonmosen/muse-video-prompt-skill/tree/0885b51e9b96da786939882751d929c186e9378b). Upstream license: [MIT](https://github.com/masonmosen/muse-video-prompt-skill/blob/0885b51e9b96da786939882751d929c186e9378b/LICENSE). Its generation tool, snapshot parameters, and frame script are not bundled.
