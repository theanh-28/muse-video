---
name: anistudio-drama-workbench
description: "Turn an animation brief or supplied script into a dramatic episode plan, character/world/prop bibles, and shot coverage that fits this project's YAML schema. Use when developing or revising story, bibles, or storyboard; it does not generate or submit media."
---

# Anistudio Drama Workbench

Use this skill for story and storyboard work. The selected project files and Pydantic models remain the source of truth; do not create a second competing project format.

## Before authoring

1. Read `AGENTS.md`, `docs/RESEARCH_NOTES.md`, `docs/CONTINUITY_SPEC.md`, the selected `project.yaml`, the current episode, and its Bible/ledger files.
2. If a script or existing creative document is supplied, treat its approved facts as constraints. Record gaps or contradictions for review instead of silently resolving changes to approved material.
3. Confirm requested audience, language, aspect ratio, duration, genre, and visual-style locks. Keep all new creative material `DRAFT` until the user approves it.

## Story and shot workflow

1. Express the story's protagonist, goal, obstacle, and meaningful change in the logline and synopsis. Arrange the key turn and payoff to fit the requested duration; do not force a formula when the brief calls for another shape.
2. Establish only the character, location, and prop facts needed to produce the episode. Give each stable entity a stable ID. Put invariant appearance and costume facts in the Character Bible; put fixed geography, landmarks, lighting/palette locks, and prop ownership/state rules in the World Bible.
3. Give each shot a specific story purpose: what new information, choice, action, or relationship change the audience receives. Cover the supplied script's material beats, or identify omitted beats with a reason when the project format allows it.
4. Write every shot as a readable `start_state` → ordered, visible `action_beats` → `end_state`. Keep hands, held props, screen position, eyeline, environment, camera state, light, and story state coherent across dependent shots.
5. Choose a framing and angle that serve the beat. Describe one motivated primary camera movement, or say the camera is fixed. State the movement's start and stop when it matters. Keep lighting and palette consistent with the World Bible.
6. Choose the shot count and each shot's duration from the story's distinct visual beats, action complexity, continuity needs, and requested episode runtime. The user supplies the story and episode runtime; the agent decides shot count and shot timing. In the Studio workflow, choose 5–8 shots. Each shot is one Muse video request and must be 10 seconds or shorter; choose an intentional whole-second duration. If an action needs longer, split it at meaningful story beats into multiple shots and preserve their continuity. Do not add arbitrary micro-shots just to fit the limit, pad the story to reach a count, or divide runtime evenly by default; use equal durations only when the intended rhythm supports them. Leave room for meaningful reactions or pauses, and keep total shot duration within the requested episode tolerance.
7. For groups or changing geography, define who is where, which direction they face, what separates them, and the screen direction of movement. Use the narrow 9:16 frame with foreground/midground/background depth where relevant. Do not invent safe areas for platform UI unless the project requested them.
8. Describe only real references in `references`. If an image does not exist, use `reference_plan` to say what is needed; never invent a path or imply that a planned image was supplied.

## Project mapping and checks

- Story intent belongs in `project-bible.md`; identity and setting locks belong in the Bible YAML files; shot purpose, states, beats, camera, lighting, audio, references, dependencies, and QA checks belong in `episodes/<EP>/episode.yaml`.
- This project has no separate screenplay schema. Keep authored production truth in the supported project files; add a separate script file only when the project explicitly needs it, and do not let it conflict with the episode YAML.
- Keep IDs stable when revising a shot. If a change affects downstream state, list dependent shots for re-review instead of updating them silently.
- Run `storyboard validate` before preparing prompts. Validation checks structure and references; it does not prove a story works or a generated clip follows the plan.
- This skill prepares DRAFTs only. It does not approve content, estimate an unmeasured quota cost, call a provider, or bypass a generation gate.

## Further guidance

See [shot design checklist](references/shot-design-checklist.md) for coverage, blocking, action timing, and revision checks.

## Source adaptation

This local workflow is independently rewritten for the project's schema, drawing selectively on `short-drama-storyboard` and `short-drama-video-prompts` from [zenstory-ai/drama-skills at 37232f6d22e174c36e321d2e3a1a3ae871e7d602](https://github.com/zenstory-ai/drama-skills/tree/37232f6d22e174c36e321d2e3a1a3ae871e7d602). Upstream license: [MIT](https://github.com/zenstory-ai/drama-skills/blob/37232f6d22e174c36e321d2e3a1a3ae871e7d602/LICENSE). No upstream files or scripts are bundled.
