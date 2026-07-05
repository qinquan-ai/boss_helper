# Senders — Python & other languages

**Architecture:** there is **one** receiver + dashboard (the Node one — `npx @qin16778/tracelink@latest board`, see [dashboard.md](dashboard.md)). Every language ships a **sender** only: the `TraceLog` schema + a minimal tracer + an HTTP transport that POSTs events to that shared receiver. You **rarely need a per-language receiver** — one Node receiver serves senders written in any language. Full normative contract: [CONFORMANCE.md](https://github.com/qinquan-ai/Trace_Link/blob/main/senders/CONFORMANCE.md).

## Python sender

`pip install tracelink` (add `[fastapi]` for the middleware). **Sender-only** — there is no Python CLI/receiver; point it at the Node board.

```python
from tracelink import debug_tracer

# One-line HTTP sink → the shared board on 5174 (returns the sink so you can .flush())
sink = debug_tracer.configure(http_endpoint="http://127.0.0.1:5174/__debug_log")

debug_tracer.start_scope('delete-work')
debug_tracer.entry('router.py:delete', 'user clicked delete', {'id': 123}, scope='delete-work')
debug_tracer.db('repo.py:remove', 'DELETE row', {'id': 123}, scope='delete-work')
debug_tracer.end_scope('delete-work')
```

Or build the sink explicitly and register it:

```python
from tracelink import debug_tracer
from tracelink.sinks.http import HttpSink
off = debug_tracer.add_sink(HttpSink(endpoint="http://127.0.0.1:5174/__debug_log"))  # default endpoint is this
```

FastAPI / Starlette middleware (needs the `[fastapi]` extra) auto-reads the `x-trace-id` / `x-debug-scopes` headers a JS sender injects, so a frontend chain and its backend continuation line up automatically:

```python
from fastapi import FastAPI
from tracelink import TraceMiddleware
app = FastAPI()
app.add_middleware(TraceMiddleware)
```

The HTTP sink is **non-blocking** (POSTs on a background daemon thread, drops on a full queue) and **fail-safe** (swallows all network errors), using only stdlib `urllib.request`. Python is env-gated: it's enabled when `DEBUG`/`DEV` is set, or forced via `TRACELINK_ENABLED=true`/`false`; scope filter via `TRACELINK_SCOPES` (`*` or comma-separated).

> **Do not** hand-set `x-trace-id` / `x-debug-scopes` — the sinks inject them.

## Building a sender in any language

A conformant sender must:

1. **Serialize each event as a schema-valid `TraceLog`** with all required fields and **camelCase keys on the wire** (see [wire-schema.md](wire-schema.md)).
2. **Sanitize `data`** before send (redact secrets, drop non-serializable, bound depth/size).
3. **Normalize `layer`** at emit: keep `FE-`/`BE-`/`X-`, else prefix `X-`.
4. **POST to `/__debug_log`** (one JSON object per request, `Content-Type: application/json`) at the receiver (default `http://127.0.0.1:5174/__debug_log`, configurable / `TRACELINK_PORT`). Attach `x-trace-id: <traceId>` and `x-debug-scopes: <JSON string[]>` headers. Receiver replies `204` (or `400` on bad JSON) — ignore the body.
5. **Be strictly non-blocking & fail-safe** — fire-and-forget with a short timeout (~2s); swallow all network/DNS/timeout/non-2xx errors; never throw into caller code; no-op cleanly if the transport is unavailable.
6. **Fill `parentSpanId` from native ambient context** and honor explicit overrides. Use the idiomatic primitive: Go `context.Context`, Java/Kotlin `ThreadLocal`/coroutine context, .NET `AsyncLocal<T>`, Rust task-locals, etc. If no safe ambient mechanism exists, support explicit `parentSpanId` threading and document the limitation.
7. **Implement the span open + close lifecycle:** emit a span-open, run the fn, then emit a span-close with the **same `spanId`/`traceId`** carrying `durationMs` + `async` — for both sync and async fns. Pair by `spanId`; the close event is the one with `durationMs`.
8. **Treat missing `level`/`outcome` as defaults** (absent `outcome` ⇒ `call`); carry the outcome reason as `data.reason` (never a top-level `reason`).

Reference implementations to mirror: JS `src/`, Python `senders/python/tracelink/`. Golden round-trip fixtures live in `senders/fixtures/`. The full spec (RFC-2119 MUST/SHOULD/MAY, conformance checklist) is the authoritative [CONFORMANCE.md](https://github.com/qinquan-ai/Trace_Link/blob/main/senders/CONFORMANCE.md).

## JS sender wiring (reference)

```typescript
// Browser: POSTs to '/__debug_log' by default (same origin)
import { tracer } from '@qin16778/tracelink';
import { HttpSink } from '@qin16778/tracelink/browser';
tracer.configure({ httpSink: new HttpSink() });
```
```typescript
// Node (Express / Hono / Next.js API / Electron main) — absolute endpoint required
import { tracer } from '@qin16778/tracelink';
import { NodeHttpSink } from '@qin16778/tracelink/node'; // side-effect: installs async span context
tracer.configure({ httpSink: new NodeHttpSink({ endpoint: 'http://127.0.0.1:5174/__debug_log' }) });
```

`HttpSink` (browser) / `NodeHttpSink` (Node) options: `endpoint`, `disabled`, `getEnabledScopes` (browser); plus `timeoutMs` (default 2000) and `extraHeaders` (Node). Both auto-inject the correlation headers.
