# Wire schema — the `TraceLog` data contract

Every event serializes to **one JSON object**, round-trippable as one NDJSON line. Field names are **camelCase on the wire in both languages** (Python emits camelCase keys even though its call surface is snake_case). Authoritative source: `src/core/types.ts` (`interface TraceLog`); full normative spec: the [CONFORMANCE.md](https://github.com/qinquan-ai/Trace_Link/blob/main/senders/CONFORMANCE.md).

## Fields

### Required

| Field | Type | Notes |
|---|---|---|
| `ts` | string | Local time `[HH:mm:ss.SSS]`. Human-readable, not for cross-host sorting. |
| `layer` | string | Namespaced channel; normalized at emit (see below). |
| `fn` | string | `"<file>:<function>"` convention (use `"<file>:<Class.method>"` for methods) so events are greppable. |
| `msg` | string | Short human description, no emoji. |
| `data` | object | JSON-serializable payload, **sanitized** before send. Emit `{}` when empty — never omit. |
| `traceId` | string | Correlates FE/BE events of one chain. Scope-derived (`<scope>-<timestamp6>-<rand3>`) or the scope name itself (stream mode). |
| `spanId` | string | Monotonic per-tracer counter tying events into a chain. A span's open + close share **one** `spanId`. |

### Optional

| Field | Type | Notes |
|---|---|---|
| `scope` | string | Business chain name, e.g. `"delete-work"`. Omitted when no scope active. |
| `level` | `'debug' \| 'info' \| 'warn' \| 'error'` | Severity hint for dashboard filter/color. Omit and nothing breaks. |
| `outcome` | `'call' \| 'blocked' \| 'intent'` | What actually happened. **Absent MUST be treated as `call`.** Reason lives in `data.reason` — there is **no** top-level `reason`. |
| `durationMs` | number | Elapsed wall-clock ms for a span. Present on the span **close** event only. |
| `async` | boolean | Whether the span's fn returned a thenable/coroutine. Present on the span **close** event only. |
| `parentSpanId` | string | Parent span for nested calls. Filled automatically from ambient context, or passed explicitly (explicit wins). |
| `userId` | string | Optional user id for multi-tenant backends. |

> There is **no** `phase:'END'` field and **no** top-level `reason` field. These are frozen schema decisions — do not invent them.

Example NDJSON line:

```json
{"ts":"[14:23:05.123]","layer":"FE-ACTION","fn":"Button:onClick","msg":"User clicked delete","data":{"id":123},"traceId":"delete-work-456789-abc","spanId":"span-3","scope":"delete-work"}
```

## Span open/close lifecycle

`tracer.span(entry, fn)` (JS) / `tracer.span(layer, fn, msg, func, ...)` (Python) follows an **open + close** model:

1. A fresh `spanId` is generated and a **span-open** event is emitted immediately (live visibility for long-running spans). The open event carries **no** `durationMs`/`async`.
2. `fn`/`func` runs with that span installed as ambient context — children auto-nest, sharing `traceId` and pointing `parentSpanId` at this span.
3. When it settles (sync return / Promise settle / coroutine done — including on throw), a **span-close** event is emitted with the **same `spanId` and `traceId`**, carrying `durationMs` (measured real elapsed ms) and `async`.

Rules:
- Pair open/close **by `spanId`**; **the close event is the one that has `durationMs`**.
- The close event's `parentSpanId` equals the open event's (same position in the call tree).
- All of `durationMs`/`async` are optional & backward compatible: a legacy span-open with no close is still valid/renderable.

## traceId / spanId / parentSpanId propagation

1. Starting a scope/span establishes an ambient span context `{ traceId, spanId, scope }`.
2. Any event emitted while a span is active inherits that span's id as its `parentSpanId` and gets a fresh monotonic `spanId`.
3. A child span opened inside a parent points its `parentSpanId` at the parent; closing restores the enclosing span.
4. Explicitly passing `parentSpanId` overrides the ambient value.
5. `traceId` resolution when emitting: explicit `scope` → that scope's session/derived id; else enclosing span's `traceId`; else `'no-trace'` (JS) / a synthetic `trace-<ms>` (Python).

Ambient context mechanism: JS core is synchronous; `tracelink/node` installs an `AsyncLocalStorage`-backed provider for correctness across `await`/concurrent async. Python uses `contextvars.ContextVar`, which is correct across nested calls, `await`, and concurrent asyncio tasks. Newly created OS threads require explicit context propagation.

## Layer normalization

At emit time the `layer` string is normalized: trim; if it starts with `FE-`/`BE-`/`X-` keep it; otherwise prefix `X-`. Empty falls back to `FE-ACTION`. Built-ins: `FE-ACTION`, `FE-API`, `FE-WS`, `FE-UI`, `BE-ENTRY`, `BE-INTERNAL`, `BE-DB`, `BE-WS`. Custom layers MUST be `X-*`. This auto-prefix is a safety net, not an excuse to skip the namespace.

## `outcome` + `level` semantics

- `outcome` absent ⇒ `call` (a normal, executed call). `blocked` = intercepted/rejected/not-really-executed. `intent` = wanted to but didn't (or a placeholder).
- The `blocked(...)`/`intent(...)` helpers map to `outcome` + a default `level` (`blocked` → `warn`, `intent` → `info`) + `data.reason`.
- `level` is purely a display hint; the receiver is schema-agnostic and rides optional fields (`level`/`outcome`/`durationMs`/`async`) through POST → NDJSON → SSE unchanged.

## Sanitization

Before an event leaves the process, `data` is passed through the language's sanitizer (JS `src/core/sanitize.ts`, Python `tracelink/sanitize.py`): redact obvious secrets, drop non-serializable values, bound depth/size. The receiver re-sanitizes defensively, but senders must not rely on that. Still: **don't put real secrets in `data`** — TraceLink is a debug tool, not an audit log.
