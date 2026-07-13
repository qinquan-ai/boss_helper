# Dashboard / receiver — startup and port troubleshooting

The **receiver** persists incoming events and serves the embedded single-file **dashboard**. Senders only emit; you need a running receiver to see anything.

## Start it

```bash
npx tracelink@latest dashboard     # recommended
node bin/tracelink.mjs dashboard             # from a clone of the repo root
```

- Default host **`127.0.0.1`**, default port **`5174`**.
- Prints the dashboard URL and (unless `--no-open`) opens it: `http://127.0.0.1:5174/__debug_log/ui`.
- Flags: `--port <n>`, `--host <h>`, `--no-open`, `--force`, `-h`/`--help`.

> **`npx` stale-cache gotcha:** plain `npx tracelink dashboard` may execute an older cached copy. **Always pass `@latest`** (`npx tracelink@latest dashboard`) to force the current version.

You can also embed a receiver in your app instead of running the CLI:

```typescript
// Vite (vite.config.ts) — rides the Vite dev-server port at /__debug_log
import { debugLogPlugin } from 'tracelink/receiver/vite';
export default defineConfig({ plugins: [debugLogPlugin()] });
```
```typescript
// Non-Vite (Next.js / plain Node): standalone node:http receiver, default :5174
import { startReceiverServer } from 'tracelink/receiver/http';
const server = startReceiverServer({ port: 5174 }); // server.close() to stop
```

`startReceiverServer(options)` accepts `{ port?, host?, force?, dir?, subdir?, cors?, persistScopes? }`. Port defaults to the `TRACELINK_PORT` env var, else `5174`.

## HTTP endpoints

All under the ingest path `/__debug_log` (or the Vite mount). Every response carries `x-tracelink-receiver: <version>` + permissive CORS.

| Method | Path | Behavior | Response |
|---|---|---|---|
| `POST` | `/__debug_log` | Ingest one `TraceLog` (body = one JSON object) → append one NDJSON line + one readable line | `204`; `400` on bad JSON |
| `GET` | `/__debug_log` | Read the full NDJSON buffer | `200` `application/x-ndjson` |
| `GET` | `/__debug_log?report` | Head/tail human summary (head 20 / tail 50) | `200` `text/plain` |
| `DELETE` | `/__debug_log` | Clear both trace files | `204` |
| `GET` | `/__debug_log/stream` | SSE: replay current buffer as `event: replay` frames, then push each new log as `event: log`; `: heartbeat` ~every 15s | `200` `text/event-stream` |
| `GET` | `/__debug_log/scopes` | Read `{ enabled, known }` (authoritative enabled scopes + persisted Scope catalog) | `200` JSON |
| `POST` | `/__debug_log/scopes` | Set authoritative enabled scopes (body `{ enabled }`); persists the complete Scope state | `204` |
| `DELETE` | `/__debug_log/scopes` | Reset to `{ enabled: ["*"], known: [] }`; trace history is unchanged | `204` |
| `GET` | `/__debug_log/ui` | Serve the embedded single-file dashboard | `200` `text/html` |
| `OPTIONS` | any subpath | CORS preflight | `204` |

On the standalone server, `GET /` redirects to `/__debug_log/ui`. `enabled: ["*"]` means all scopes.

## Local trace files

The receiver locates the project root (its cwd) and writes under `.tracelink/`:

```
<project-root>/.tracelink/trace.ndjson    # NDJSON, one JSON per line — for AI/scripts
<project-root>/.tracelink/trace.log        # human-readable multi-line
<project-root>/.tracelink/scopes.json      # persisted enabled scopes + discovered Scope catalog
```

Read them back:

```bash
grep '"scope":"delete-work"' .tracelink/trace.ndjson | jq .                       # one chain
grep '"traceId":"delete-work-123456-abc"' .tracelink/trace.ndjson | jq .          # by trace id across FE+BE
grep '"level":"error"' .tracelink/trace.ndjson | jq .                             # only errors
grep '"durationMs"' .tracelink/trace.ndjson | jq '{fn, msg, durationMs, async}'   # span timings (close events)
grep -E '"outcome":"(blocked|intent)"' .tracelink/trace.ndjson | jq '{fn, msg, outcome, reason: .data.reason}'
```

## The port footgun (read this before "the Dashboard is broken")

- **The configured Receiver is the authority; `5174` is only its default port.** The embedded single-file Dashboard is served by that Receiver at `/__debug_log/ui`. If you select another port, every sender and Dashboard connection must use the same address.
- **`5173` is for dashboard *developers* only.** The `debug_board` project's live source dev UI runs under **Vite on `5173`** and merely *connects to* `5174` for data. You don't need it unless you're hacking on the dashboard UI.
- **Why it bites:** Vite is a third-party tool. If `5173` is busy, Vite **auto-increments** to the next free port — which can land on **`5174` and collide with the receiver**. TraceLink deliberately does not hard-lock Vite's port.
- **`--force` is cooperative, not a kill.** `tracelink dashboard --force` only reclaims `5174` from **another TraceLink receiver** (it probes the `x-tracelink-receiver` header, then asks that receiver to shut down via `POST /__tracelink/shutdown`). Against a **foreign** process (e.g. a stray Vite that grabbed `5174`) it does **nothing** — it surfaces an actionable error and never kills unknown processes.

**Fixes when the port is occupied:**
1. Free `5173` (stop the stray Vite dev server) so Vite stops spilling onto `5174`.
2. Pick another port for the Receiver: `npx tracelink@latest dashboard --port 6000`, or set the `TRACELINK_PORT` env var. The Receiver does not auto-increment; senders must explicitly point at the selected port.
3. If another TraceLink receiver holds `5174`, reuse it or restart with `--force`.

## Security model

Receivers bind `127.0.0.1` only, have **no auth**, and are **dev-only** — a production build MUST NOT ship receiver code. Guard with `if DEBUG:` / `NODE_ENV !== 'production'`.
