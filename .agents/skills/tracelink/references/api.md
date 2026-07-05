# API reference

Per-function API for the JS core (`import { tracer } from '@qin16778/tracelink'`) and the Python sender (`from tracelink import debug_tracer`). Only functions that exist in the source are listed.

**Naming:** JS is camelCase, Python is snake_case. The biggest surface difference: **JS has a generic `tracer.log(entry)`; Python does not** — Python emits via per-layer methods (`entry`/`internal`/`db`/`ws`/`custom`). Wire field names are camelCase in both languages (see [wire-schema.md](wire-schema.md)).

---

## Emitting events

### JS — `tracer.log(entry)`

`entry` is a `TraceEntry`: required `layer`, `fn`, `msg`; optional `data`, `scope`, `level`, `outcome`, `userId`, `parentSpanId`. Most fields (`ts`, `traceId`, `spanId`, `parentSpanId`) are derived automatically.

```typescript
tracer.log({ layer: 'FE-ACTION', scope: 'delete-work', fn: 'Button:onClick', msg: 'clicked', data: { id: 1 } });
```

Convenience helpers (thin wrappers over `log`, all `(fn, msg, data?)`):

```typescript
tracer.action(fn, msg, data?);   // FE-ACTION
tracer.api(fn, msg, data?);      // FE-API
tracer.ws(fn, msg, data?);       // FE-WS
tracer.ui(fn, msg, data?);       // FE-UI
tracer.layer('BE-ENTRY'|'BE-INTERNAL'|'BE-DB'|'BE-WS', fn, msg, data?);
tracer.custom('X-RENDER', fn, msg, data?);   // any X-* custom layer
```

### Python — per-layer methods

There is no `debug_tracer.log(...)`. Emit with the layer-specific method. Signature (keyword-only after `data`): `(fn, msg, data=None, *, level=None, scope=None, user_id=None, parent_span_id=None)` — note `entry()` does **not** accept `parent_span_id`.

```python
debug_tracer.entry('router.py:delete', 'user clicked delete', {'id': 1}, scope='delete-work')  # BE-ENTRY
debug_tracer.internal('svc.py:check', 'validating', scope='delete-work')                        # BE-INTERNAL
debug_tracer.db('repo.py:remove', 'DELETE row', {'id': 1}, scope='delete-work')                 # BE-DB
debug_tracer.ws('ws.py:push', 'notify client')                                                  # BE-WS
debug_tracer.custom('X-LLM', 'agent.py:call', 'openai chat', {'model': 'gpt'})                  # X-* custom (auto-normalized)
```

---

## Spans (auto-nested, timed)

A span emits a **span-open** event immediately (no `durationMs`), runs `fn` with that span installed as ambient context (children auto-inherit `traceId` and set `parentSpanId`), then emits a **span-close** event with the **same `spanId`/`traceId`** carrying `durationMs` (real elapsed ms) and `async`. Works for sync and async fns. See [wire-schema.md](wire-schema.md) §span lifecycle.

### JS — `tracer.span(entry, fn)`

Returns `fn()`'s value. Import `@qin16778/tracelink/node` once (side-effect) for async-correct nesting across `await`.

```typescript
import '@qin16778/tracelink/node';
await tracer.span({ layer: 'X-AGENT', fn: 'agent:run', msg: 'agent.run', scope: 'agent-run' }, async () => {
  await tracer.span({ layer: 'X-TOOL', fn: 'agent:search', msg: 'tool: search' }, async () => { /* ... */ });
});
```

### Python — `debug_tracer.span(layer, fn, msg, func, *, data=None, level=None, scope=None, user_id=None)`

`func` is a zero-arg callable (sync or returning an awaitable). Returns `func()`'s value (a coroutine when async — so `await` it). Context is backed by `contextvars`, correct under `asyncio`/threads/nested `await`.

```python
async def body(): ...
await debug_tracer.span('X-AGENT', 'agent.py:run', 'agent.run', body, scope='agent-run-py')
```

---

## Outcome helpers (`blocked` / `intent`)

Set the `outcome` field and fold the reason into `data.reason` (no top-level `reason`). `blocked` defaults `level='warn'`, `intent` defaults `level='info'`.

> **Default `layer` differs by language:** JS defaults to `FE-ACTION`; Python defaults to `BE-INTERNAL`. Pass `layer` explicitly (e.g. `X-AGENT`) when tracing an agent.

### JS — `tracer.blocked(fn, msg, opts?)` / `tracer.intent(fn, msg, opts?)`

`opts`: `{ reason?, data?, layer?, level?, scope?, userId?, parentSpanId? }`.

```typescript
tracer.blocked('agent:sub', 'write outside sandbox denied', {
  reason: 'permission denied', layer: 'X-AGENT', data: { path: '/etc/passwd' },
});
tracer.intent('agent:plan', 'skipped pricey deep-research tool', {
  reason: 'cost budget exceeded', layer: 'X-AGENT', data: { tool: 'deep_research' },
});
```

### Python — `debug_tracer.blocked(fn, msg, *, reason=None, data=None, layer='BE-INTERNAL', level='warn', scope=None, user_id=None, parent_span_id=None)` / `intent(... level='info')`

```python
debug_tracer.blocked('agent.py:sub', 'write outside sandbox denied',
                     reason='permission denied', data={'path': '/etc/passwd'}, layer='X-AGENT')
debug_tracer.intent('agent.py:plan', 'skipped pricey tool',
                    reason='cost budget exceeded', data={'tool': 'deep_research'}, layer='X-AGENT')
```

---

## Scope sessions

Wrap a chain so all events share one `traceId` and you get an elapsed duration.

| JS | Python | Returns |
|---|---|---|
| `tracer.startScope(scope)` | `debug_tracer.start_scope(scope, custom_id?)` | `traceId` (string) |
| `tracer.endScope(scope)` | `debug_tracer.end_scope(scope)` | duration ms (`number`/`int`) or `null`/`None` |
| `tracer.getTraceId(scope)` | `debug_tracer.get_trace_id(scope)` | `traceId` or undefined/None |
| `tracer.getActiveScopes()` | `debug_tracer.get_active_scopes()` | `string[]` |

**Two patterns:** *session mode* (call `startScope`/`endScope` around the chain — best for parallel ops / needing elapsed time); *stream mode* (just pass `scope` on each event, the scope name becomes the `traceId` — best for singletons/continuous streams with no clear end).

---

## Scope filter (which scopes get collected)

Toggle collection at runtime without restarting. `['*']` = all enabled (default).

| JS | Python |
|---|---|
| `tracer.enableScope(scope)` | `debug_tracer.enable_scope(scope)` |
| `tracer.disableScope(scope)` | `debug_tracer.disable_scope(scope)` |
| `tracer.enableAllScopes()` | `debug_tracer.enable_all_scopes()` |
| `tracer.disableAllScopes()` | `debug_tracer.disable_all_scopes()` |
| `tracer.getEnabledScopes()` | `debug_tracer.get_enabled_scopes()` |

Let a **dashboard** flip scopes on live JS senders by opting into scopeSync (the tracer polls the receiver `/scopes` endpoint and applies the authoritative `enabled` list):

```typescript
tracer.configure({ scopeSync: { endpoint: 'http://localhost:5174/__debug_log/scopes', intervalMs: 2000 } });
tracer.stopScopeSync(); // stop polling
```

Python honors `TRACELINK_SCOPES` env (`*` or comma-separated) at startup; it has no scopeSync poller.

---

## Custom layers

Registration is **advisory** (adds description/color to summaries and console hints) — it does NOT gate emission; an unregistered `X-*` layer still emits.

```typescript
tracer.registerLayer('X-RENDER', { description: 'Three.js frame', color: '#88ff88' });
tracer.getRegisteredLayers();
```
```python
debug_tracer.register_layer('X-RENDER', { 'description': 'Three.js frame', 'color': '#88ff88' })
debug_tracer.get_registered_layers()
```

---

## Custom sinks (forward to OTel / Datadog / your collector)

`addSink(fn)` registers a `(log) => void` callback that receives every event; returns an unregister function. Keep it non-blocking (don't `await` on the hot path).

```typescript
const off = tracer.addSink((log) => myCollector.send(log));
off(); // unregister
```
```python
off = debug_tracer.add_sink(lambda log: my_collector.send(log))
off()
```

JS also has `tracer.configure({ httpSink })` for the single reconfigurable HTTP sink slot. Python has `debug_tracer.configure(http_endpoint=..., http_sink=..., http_timeout_ms=2000, http_extra_headers=..., http_disabled=False)` which builds/installs a non-blocking HTTP sink and returns it (so you can `.flush()` before exit).

---

## Master switch, memory & inspection

| Purpose | JS | Python |
|---|---|---|
| Enable / disable all sinks | `tracer.enable()` / `tracer.disable()` | `debug_tracer.set_enabled(bool)` |
| Query enabled | `tracer.isEnabled()` | `debug_tracer.is_enabled()` |
| In-memory counts summary | `tracer.summary()` → `{ total, byLayer, byScope }` | *(no equivalent)* |
| All buffered logs | `tracer.allLogs()` | `debug_tracer.get_logs()` |
| Clear in-memory buffer | `tracer.clearMemory()` | `debug_tracer.clear()` |
| Delete the on-disk trace files | *(via receiver `DELETE /__debug_log`)* | `debug_tracer.reset_files()` |

> **Honest gaps:** Python has **no** `summary()` and **no** generic `log()`. JS `clearMemory()` only clears the in-memory ring buffer (default cap 1000), not the `.tracelink/` files — to clear files, use the receiver's `DELETE /__debug_log` (see [dashboard.md](dashboard.md)).

---

## Package entry points

**JS `@qin16778/tracelink` subpaths** (from `package.json` `exports`):

| Import | Exports |
|---|---|
| `@qin16778/tracelink` | `tracer`, `scopeController`, `MemorySink`, `BUILTIN_LAYERS`, `isBuiltinLayer`, `isCustomLayer`, `normalizeLayer`, `sanitize`, `sanitizeData`, `formatTs`, `makeTraceId`, `makeSpanId`, `now`, `currentSpan`, `runInSpan`, `setContextProvider`, `StackContextProvider` + types |
| `@qin16778/tracelink/browser` | `HttpSink`, `installAutoClick`, `enableAutoClick`, `disableAutoClick` |
| `@qin16778/tracelink/browser/auto-click` | auto-click instrumentation only |
| `@qin16778/tracelink/node` | `NodeHttpSink`, `AlsContextProvider`, `installNodeAsyncContext` — **side-effect:** importing installs `AsyncLocalStorage` span context |
| `@qin16778/tracelink/receiver/http` | `startReceiverServer`, `createReceiverHandler`, `RECEIVER_VERSION` |
| `@qin16778/tracelink/receiver/vite` | `debugLogPlugin` |

**Python `tracelink` package** exports: `debug_tracer` (singleton), `DebugTracer`, `Sink`, `HttpSink`, `TraceMiddleware` (lazy — needs the `[fastapi]` extra), `SpanContext`, `current_span`, `TraceLayer`, `TraceLog`, `LogLevel`, `Outcome`, `TraceOutcome`, `BUILTIN_LAYERS`, `is_builtin_layer`, `is_custom_layer`, `normalize_layer`, `__version__`.

Sink wiring examples (HttpSink / NodeHttpSink / Vite / node:http receiver / FastAPI middleware) are in [senders.md](senders.md) and [dashboard.md](dashboard.md).
