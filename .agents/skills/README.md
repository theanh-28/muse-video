# Project-local Agent Skills

These skills are adapted for this repository's YAML/Pydantic source of truth and gated production workflow. They do not install third-party packages, copy upstream scripts, or submit media.

## Routing

| Skill | Use it for | Primary project artifacts |
|---|---|---|
| `anistudio-story-continuity` | Project rules, continuity-ledger updates, and approval boundaries; use as the general router. | Project config, Bible, episode, continuity ledger, generation manifest |
| `anistudio-drama-workbench` | Turning an idea or supplied script into dramatic structure, bibles, and shot coverage. | `project-bible.md`, `assets/*bible.yaml`, `episodes/<EP>/episode.yaml` |
| `anistudio-muse-prompting` | Writing or reviewing one-shot prompts for the configured Muse provider. | `episodes/<EP>/prompts/`, one-shot manifest |
| `anistudio-cinematic-qa` | Camera/light planning and evidence-based clip/continuity review. | Storyboard camera/light fields, frames, QC report, continuity ledger |

Select the smallest relevant set. Drama planning sets the story intent; Muse prompting turns an approved shot into provider-facing language; cinematic QA checks the produced media. Continuity rules apply across all three.

## Provenance

Three upstream repositories are selectively used as references at the pinned commits recorded in `docs/THIRD_PARTY_SKILLS.md`. The local skills are rewritten to match this repository. No upstream scripts, schemas, sample assets, browser automations, or provider calls are bundled.
