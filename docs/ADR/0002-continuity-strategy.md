# ADR 0002 — Continuity Strategy

- **Status:** Accepted for MVP implementation
- **Date:** 2026-11-16

## Context

Storyboard end states are expectations. The Continuity Ledger must describe the actual reviewed clip whenever generated media differs. Muse2API's current source accepts image and video reference fields, but native snapshot continuation is absent from the request model; reference quality has not been verified on the user's account.

## Decision

1. Every shot stores a continuity level, start state, end state, action beats, camera, audio, reference plan and QA checks.
2. C3 shots depend on the previous shot and are submitted sequentially. A shot cannot advance if its predecessor is missing or not reviewed.
3. After an imported/generated clip exists, inspect the media with ffprobe, extract first/middle/last frames, and review it before updating the ledger or preparing its dependent prompt.
4. Prefer provider-native continuation only when its capability is documented and a real output has demonstrated it. Otherwise use a last-frame image reference when that exact provider path has been verified. Otherwise use prompt-only continuity with an explicit risk and an edit plan such as a match cut or establishing shot.
5. The ledger stores observations, reviewer notes, frame paths, status and risks. It does not infer face identity or claim seamless continuity.

## Consequences

- Continuity work is intentionally serial for dependent shots.
- Storyboard validation can verify dependency structure but cannot prove visual matching.
- ManualProvider requires a person to review imported clips and enter observed state; the CLI cannot claim that media was generated or inspected unless those actions are recorded.

## Rollback

Continuity levels and observations are durable project data. If a rule changes, keep existing observations and add an explicit migration or decision note; do not overwrite an observed ledger with storyboard predictions.
