# Application modules

- `core/`: Pydantic project, episode, shot, job and continuity models.
- `providers/`: provider protocol, non-networking ManualProvider and gated experimental Muse2API client.
- `services/`: prompt compilation, manifest approval fingerprint and job transitions.
- `media/`: ffprobe, first/middle/last frame extraction, render command construction and QC.
- `storage/`: project-local YAML/JSON reads and guarded writes.
- `cli/`: Typer command groups exposed as `anistudio`.

The experimental provider reads only a gateway bearer key from the environment. It does not collect Muse cookies. Live submission is disabled unless the exact manifest is approved and the user confirms the submit action.
