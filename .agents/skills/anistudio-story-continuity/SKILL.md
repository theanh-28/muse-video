---
name: anistudio-story-continuity
description: "Draft and maintain this project's episode scripts, character/world/prop bibles, shot storyboards, prompts and continuity ledger. Use for animation project authoring in this repository; it does not submit media generation."
---

# Anistudio Story Continuity

Use the project files as the source of truth. Before planning production, read `docs/RESEARCH_NOTES.md`, `docs/CONTINUITY_SPEC.md`, the project configuration and the current episode files. The project CLI and schemas define the accepted structure.

## Skill routing

Use this skill as the project-wide safety and continuity router. For focused work, also consult the smallest relevant specialized skill:

- Story structure, bibles, shot coverage, blocking, or storyboard revision: `.agents/skills/anistudio-drama-workbench/SKILL.md`.
- Provider-facing prompt composition, reference mapping, or a one-shot manifest: `.agents/skills/anistudio-muse-prompting/SKILL.md`.
- Camera/light planning or written evidence-based review of generated clips and joins: `.agents/skills/anistudio-cinematic-qa/SKILL.md`.

The local Codex web workflow receives this router as part of its explicit project context. Keep the following shared rules here so its isolated structured calls also apply the specialized practices: make shot purpose and visible action specific; choose a motivated camera and consistent light; build a prompt from approved shot data and currently evidenced provider capabilities; review media with frame/time/report evidence and separate observation from inference. These skills do not override the project's approval, generation, or continuity gates.

## Authoring workflow

- Keep script, Character Bible, World/Location Bible, Prop Bible, storyboard, prompt package and Continuity Ledger in the selected project/episode directories.
- Keep creative changes in `DRAFT` until the user accepts them. Do not silently change an accepted identity, visual style, costume, prop or location lock.
- A complete shot records its story purpose, cast, `start_state`, chronological `action_beats`, `end_state`, camera, lighting, audio, reference plan, continuity level, dependencies, prompt and observable QA checks.
- Keep prompt text consistent with the approved locks and the current provider capability evidence. Unknown duration, aspect-ratio, reference or continuation support stays unknown.
- Use `storyboard validate` before packaging prompts. Use `prompts build` to save the exact prompt for each shot. Do not send a DRAFT prompt or storyboard to a provider.

## Continuity handoff

- Treat the ledger as observed media state. A planned `end_state` is not an observation.
- For dependent shots, review and inspect the preceding clip first. Record the first/middle/last frame paths, actual end state, notes and risks before preparing the next shot prompt.
- Run dependent C3 shots sequentially. Prefer native continuation only after it is documented and tested; next use a verified image-reference route; otherwise plan a prompt-only match/edit and label its risk.
- Describe what is visible and distinguish observation from inference. Do not promise face identity or seamless continuity.

## Generation boundary

This skill prepares production documents only. `generation plan` creates a local manifest. A real request requires a reviewed manifest, a non-empty usage estimate, a user-approved budget and explicit submission confirmation. The skill does not approve a budget or trigger generation on its own.
