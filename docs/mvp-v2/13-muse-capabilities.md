# Muse image task capability boundary

The Studio adapter now exposes the gateway's asynchronous image-task contract: one image task per request, `POST /v1/images/tasks`, polling via `GET /v1/images/tasks/{task_id}`, and a required idempotency key. The adapter defaults to disabled submission and reports ambiguous POST failures without retrying.

This is source-supported and contract-tested only. It is not live-verified and does not authorize image generation; appearance scope approval and durable attempt persistence remain required before the Studio can enable it.
