# Muse image task capability boundary

The Studio adapter now exposes the gateway's asynchronous image-task contract: one image task per request, `POST /v1/images/tasks`, polling via `GET /v1/images/tasks/{task_id}`, result download from the configured gateway origin, and a required idempotency key. It accepts the gateway's documented single-image `data[0].url` result shape. The adapter defaults to disabled submission and reports ambiguous POST failures without retrying.

This is source-supported and contract-tested only. It is not live-verified and does not authorize image generation; `24-generation-safety.md` supplies the required scope approval and durable attempt primitives, but the Character Appearance service/UI has not yet wired them into a live operation.
