# ADR 0001 — Provider Integration

- **Status:** Accepted for MVP implementation; live Muse2API enablement is deferred
- **Date:** 2026-11-16

## Context

The project needs an operational workflow before a video provider is proven. The user requires a reviewed manifest and usage budget before any real video is created. The current Muse account could not be inspected in the browser during the audit. Muse2API source was inspected statically at commit `19db32a3d6ef50dc87567a8ee0e35dd50c8f7837`; it provides a local, reverse-engineered HTTP gateway, but a real request has not been made. Meta's official Model API documentation reviewed on this date documented image generation and video understanding, but not video generation.

## Options

| Option | Benefits | Risks / limits |
|---|---|---|
| A. Muse2API local gateway | Async task IDs, task polling, local media URLs and reference-media fields; can support automation if the account and upstream UI continue to work. | Unofficial reverse-engineered UI; session cookies are stored by the gateway; schema/UI/region/permission changes can break it; submitted work may consume account usage; duration/aspect ratio and reference behavior are not guaranteed. No account request has been tested. |
| B. Muse web with manual handoff | Works without inventing an API; Codex/CLI can manage prompts, shot order, imported media and continuity records; user remains in control of browser submissions. | Browser operations and task IDs are not automated; account access remains unknown; manual import/review is required. |
| C. Official video-generation API later | A supported contract could improve stability, task handling and billing clarity. | No suitable official video-generation endpoint was found in the reviewed official Meta Model API docs; availability and capabilities must be checked again before adoption. |

## Decision

Use **B, ManualProvider, as the default MVP provider mode**. Keep the provider protocol independent. Implement A only as an isolated experimental adapter with live submission disabled by default. The adapter must not collect or persist Muse cookies; it may read a local gateway bearer key from an environment variable. It must use one request at a time, stop on authentication/provider errors, avoid resubmitting POST after an uncertain timeout, and download only media from the configured gateway origin.

A live Muse2API smoke request is not part of this implementation turn because it creates real media and could consume usage. Enablement requires an exact manifest, user-supplied usage estimate and budget limit, explicit approval, and an explicit submission confirmation. Mocked adapter tests are implementation tests only, not proof of live compatibility.

## Consequences

- Prompt preparation, validation, manifests, job records, manual media import, continuity review and FFmpeg export remain usable without Muse2API.
- ManualProvider status represents a handoff/import state; it must never be presented as proof that Muse generated a clip.
- Provider capabilities are recorded with their evidence source and verification status. Unknown limits stay unknown.
- The MVP does not depend on any third-party skill or provider-specific browser automation.

## Rollback

Set `provider.mode: manual` and leave the experimental adapter unused. No project storyboard, Bible or media needs migration. If upstream behavior changes or any gateway auth/session error occurs, stop the queue, preserve task state and return to manual mode. A later official API can be added behind the same provider protocol.
