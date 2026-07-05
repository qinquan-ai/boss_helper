---
name: tracelink
description: Dev-time full-stack + AI-agent tracing (spans, outcome, level, NDJSON). Use when instrumenting code for observability, debugging a request/agent chain end-to-end, tracing what an AI agent did (which tools ran, what got blocked/skipped, how long each step took), or building a trace sender in another language.
---

# TraceLink

TraceLink is a **dev-time tracer**: you call `tracer.log(...)` / `tracer.span(...)`
in your code, each call becomes **one NDJSON line** persisted under `.tracelink/`
by a local receiver, and you (the AI) read those lines back to reconstruct
exactly what happened. Its flagship use is **watching an AI agent think and
act**: auto-nested spans (shared `traceId` + `parentSpanId` across `await`),
real `durationMs`/`async` per step, and explicit `outcome`s
(`call`/`blocked`/`intent`).

## When to use this skill

Use it when the user asks you to:

- **Add observability** — "add tracing to this module", "instrument the API".
- **Debug a chain** — "why does delete fail?", "trace the cancel-task flow".
- **Trace an AI agent** — "show me what the agent did", "why did it skip that tool?", "where did it get blocked?".
- **Understand unfamiliar code** — "what happens when I click X?".
- **Send traces from a non-JS project** — Python, or building a sender in any language.

Do **not** use it when: the user only wants production logging (use
`console.log` / stdlib `logging`); the bug is a syntax error (use a debugger); or
you're in a production build (traces are tree-shaken / env-gated out — never ship
live tracing or receiver code to prod).

## Install what you need

```bash
npm i @qin16778/tracelink        # JS/TS sender (browser + Node), the board CLI, receiver — npm 0.5.0
pip install tracelink            # Python sender (add [fastapi] for the middleware) — PyPI 0.6.0
npx skills add qinquan-ai/Trace_Link   # install this skill into an agent
```

To **see** traces you also need the board (receiver + dashboard) running:

```bash
npx @qin16778/tracelink@latest board   # receiver on 127.0.0.1:5174, opens the dashboard
node bin/tracelink.mjs board           # from a checkout of the repo
```

- Dashboard UI: `http://127.0.0.1:5174/__debug_log/ui`; ingest: `POST /__debug_log`.
- **Always use `@latest`** — plain `npx @qin16778/tracelink board` may run npx's
  stale cache. Port/troubleshooting details: [`references/dashboard.md`](references/dashboard.md).

## Quickstart

JS/TS — import the tracer, emit a log, wrap a step in a span:

```typescript
import { tracer } from '@qin16778/tracelink';
import '@qin16778/tracelink/node'; // once: async-correct span nesting across await (Node)

tracer.startScope('delete-work');
tracer.log({ layer: 'FE-ACTION', scope: 'delete-work', fn: 'Button:onClick', msg: 'clicked delete', data: { id: 123 } });

await tracer.span({ layer: 'BE-DB', fn: 'db.ts:remove', msg: 'delete row', scope: 'delete-work' }, async () => {
  await db.remove(123); // close event carries real durationMs + async:true
});

tracer.endScope('delete-work');
```

Python — `debug_tracer`, point it at the board, emit:

```python
from tracelink import debug_tracer
debug_tracer.configure(http_endpoint="http://127.0.0.1:5174/__debug_log")

debug_tracer.start_scope('delete-work')
debug_tracer.entry('router.py:delete', 'user clicked delete', {'user_id': 123}, scope='delete-work')
debug_tracer.end_scope('delete-work')
```

To ship events to the board from the browser (not just the local sink), wire a
sink once — `HttpSink` POSTs to `/__debug_log` by default:

```typescript
import { HttpSink } from '@qin16778/tracelink/browser';
tracer.configure({ httpSink: new HttpSink() });
```

For Node use `NodeHttpSink` from `@qin16778/tracelink/node` (absolute endpoint
required). Sink/entry-point details in [`references/api.md`](references/api.md)
and [`references/senders.md`](references/senders.md).

## Core usage & key constraints

Get these right or the dashboard/consumers misbehave:

- **Field names are `fn` and `msg`** — NOT `function` / `message`. `fn` uses the
  `"<file>:<function>"` convention so events are greppable.
- **Every event should have a `scope`** (a named business chain), or be nested
  inside a span that carries one — orphan events are noise. **Naming rule:**
  `{verb}-{noun}` in kebab-case (`delete-work`, `cancel-task`) — not
  `delete` (too generic), `cancelTask` (wrong case), or `edit_image` (snake_case).
- **`layer` is a namespaced channel.** Built-ins: `FE-ACTION`, `FE-API`, `FE-WS`,
  `FE-UI`, `BE-ENTRY`, `BE-INTERNAL`, `BE-DB`, `BE-WS`. Anything custom **must**
  be `X-*` (`X-AGENT`, `X-LLM`, `X-TOOL`). Non-prefixed names are auto-prefixed
  `X-`. Don't rename built-ins — dashboards filter by exact match.
- **Outcome reasons go in `data.reason`** — there is NO top-level `reason` field.
  Use `tracer.blocked(...)` for a denied/guardrailed call and `tracer.intent(...)`
  for a wanted-but-skipped action.
- **Spans emit two events** (open, then close). The close event is the one with
  `durationMs`/`async`; both share one `spanId`. There is no `phase` field.
- **Don't put secrets in `data`** (it's sanitized, but truncate tokens yourself),
  don't log inside tight loops/frames, and don't hand-set `x-trace-id` /
  `x-debug-scopes` headers (sinks inject them).
- **The npm package is one package with subpaths:** core `@qin16778/tracelink`;
  `/browser` (`HttpSink`, `installAutoClick`); `/node` (`NodeHttpSink`, async
  span context — side-effect import); `/receiver/http` (`startReceiverServer`);
  `/receiver/vite` (`debugLogPlugin`).

These constraints can also be enforced project-wide via a Cursor project rule (a
`.cursor/rules/*.mdc` file) if the user wants — this skill does not create one.

## References

Route to the deep detail you need (all in-directory relative links):

- [`references/api.md`](references/api.md) — per-function API for JS `tracer.*`
  and Python `debug_tracer.*` (signatures + examples; camelCase vs snake_case;
  what exists in one language but not the other).
- [`references/wire-schema.md`](references/wire-schema.md) — the `TraceLog` data
  contract: full field list, `traceId`/`spanId`/`parentSpanId` propagation,
  layer normalization, `outcome`/`level` semantics, span open/close lifecycle.
- [`references/dashboard.md`](references/dashboard.md) — how the board works,
  every receiver endpoint, the port model, and the `5173`/`5174` port footgun
  (Vite stealing `5174`; `--force` is cooperative, not a kill).
- [`references/senders.md`](references/senders.md) — the Python sender, and how
  to build a sender in any language against the one Node receiver.

Further reading (absolute GitHub URLs — safe once this skill is installed):
the repo [qinquan-ai/Trace_Link](https://github.com/qinquan-ai/Trace_Link), the
full wire/transport spec
[senders/CONFORMANCE.md](https://github.com/qinquan-ai/Trace_Link/blob/main/senders/CONFORMANCE.md),
and the runnable cross-language flagship demo
[examples/ai-agent](https://github.com/qinquan-ai/Trace_Link/tree/main/examples/ai-agent)
(`agent.mjs` / `agent.py`).

## Self-check before finishing

- [ ] `startScope`/`endScope` paired (or you used `span(...)`).
- [ ] Every event has a `scope` (or is nested in a span that carries one).
- [ ] `layer` is a built-in or a namespaced `X-*`.
- [ ] `scope` is `{verb}-{noun}` kebab-case.
- [ ] Field names are `fn`/`msg` (not `function`/`message`).
- [ ] Outcome reasons in `data.reason`; no top-level `reason`.
- [ ] No secrets in `data`.
- [ ] Production build ships no live `tracer.*` calls or receiver code.
