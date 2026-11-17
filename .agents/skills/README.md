# Project-local Agent Skills

Animation skills are adapted for this repository's YAML/Pydantic source of truth and gated
production workflow. The four selected YouTube Agent Pro skills are selectively copied with their
audited helpers and MIT notices; none of these skills submits media or publishes to YouTube.

## Routing

| Skill | Use it for | Primary project artifacts |
|---|---|---|
| `anistudio-story-continuity` | Project rules, continuity-ledger updates, and approval boundaries; use as the general router. | Project config, Bible, episode, continuity ledger, generation manifest |
| `anistudio-drama-workbench` | Turning an idea or supplied script into dramatic structure, bibles, and shot coverage. | `project-bible.md`, `assets/*bible.yaml`, `episodes/<EP>/episode.yaml` |
| `anistudio-muse-prompting` | Writing or reviewing one-shot prompts for the configured Muse provider. | `episodes/<EP>/prompts/`, one-shot manifest |
| `anistudio-cinematic-qa` | Camera/light planning and evidence-based clip/continuity review. | Storyboard camera/light fields, frames, QC report, continuity ledger |
| `yt-package` | Drafting title options and title/thumbnail pairings grounded in a finished video. | `episodes/<EP>/metadata/` |
| `yt-thumbnail` | Reviewing thumbnail text and writing thumbnail concepts/prompts from actual footage. | `episodes/<EP>/metadata/thumbnail-concepts.md`, `thumbnail-prompts.md` |
| `yt-seo` | Writing accurate titles, descriptions, tags, and relevant hashtags. | `episodes/<EP>/metadata/` |
| `yt-chapters` | Drafting and checking chapters against actual footage and timestamps. | `episodes/<EP>/metadata/chapters.txt` |

Select the smallest relevant set. Drama planning sets the story intent; Muse prompting turns an approved shot into provider-facing language; cinematic QA checks the produced media. Continuity rules apply across all three.

## Provenance

The three animation skill sources are mapped in `docs/THIRD_PARTY_SKILLS.md`. The YouTube skills
come from the pinned MIT revision documented there; only four workflows, their required helper
scripts, and shared references are included. No OAuth client, account integration, or upload flow
is bundled. See `docs/YOUTUBE_METADATA_WORKFLOW.md` for the allowlist, local adaptations, evidence
requirements, and validation steps.
