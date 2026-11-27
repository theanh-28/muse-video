# MVP v2 workflow (implemented boundary)

`BRIEF_RECEIVED → SCRIPT_GENERATING → SCRIPT_REVIEW → SCRIPT_APPROVED → ASSET_PREPARATION → … → EXPORTED`

Only the first four states are executable in this session. Approval is recorded against the exact content hash of the current script revision. Any later artifact must declare its dependencies and must not consume `STALE` or `SUPERSEDED` revisions. M3–M9 will implement the remaining transitions; no route currently bypasses their future approvals.

`ASSET_PREPARATION` is now entered atomically for an approved script when appearance specs are prepared: the run and workflow status are synchronized. Appearance request scopes bind their exact canonical provider request before a durable attempt is reserved. The later `ASSET_REVIEW → ASSETS_APPROVED` bundle gate remains unimplemented.
