/**
 * Boss 助手前端调试追踪器
 *
 * Layer:
 *   FE-ACTION - 用户操作/点击（自动监听与捕获点击）
 *   FE-API   - 前端 API 调用
 *   FE-WS    - 前端 WebSocket 消息
 *
 * Scope:
 *   collect-start - 分析任务启动
 *   collect-stop - 分析任务停止
 *   ws-event    - WebSocket 消息
 *   error       - 错误
 *
 * 自动捕获 document 所有 click 事件，用户无需手动埋点。
 * 通过 /__debug_log 端点实时写入 .cursor/debug.log + .RandP/debug.log
 */

export type TraceLayer = "FE-ACTION" | "FE-API" | "FE-WS" | "FE-UI";

interface TraceLog {
  ts: string;
  layer: TraceLayer;
  fn: string;
  msg: string;
  data: Record<string, unknown>;
  traceId: string;
  spanId: string;
  scope?: string;
}

// 全局开关
let enabled = true;
// Span 计数器
let spanCounter = 0;
// 活跃追踪 { scope -> { id, startTime } }
const activeTraces = new Map<string, { id: string; startTime: number }>();
// Scope 开关（默认全开）
let enabledScopes = new Set<string>(["*"]);

function generateSpanId(): string {
  return `span-${++spanCounter}`;
}

function formatTime(): string {
  const d = new Date();
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  const ms = String(d.getMilliseconds()).padStart(3, "0");
  return `${h}:${m}:${s}.${ms}`;
}

function getTraceId(scope?: string): string {
  if (scope) {
    const info = activeTraces.get(scope);
    return info?.id ?? `no-trace`;
  }
  return "no-trace";
}

function isScopeEnabled(scope: string): boolean {
  if (enabledScopes.has("*")) return true;
  if (enabledScopes.size === 0) return false;
  return enabledScopes.has(scope);
}

function extractScopeFromTraceId(traceId: string): string | null {
  if (!traceId || traceId === "no-trace") return null;
  const match = traceId.match(/^([a-zA-Z-]+)-\d{6}-/);
  if (match) return match[1];
  return traceId;
}

function isTraceIdEnabled(traceId: string): boolean {
  if (enabledScopes.has("*")) return true;
  if (enabledScopes.size === 0) return false;
  const scope = extractScopeFromTraceId(traceId);
  if (!scope) return true; // 无法提取时默认允许
  return enabledScopes.has(scope);
}

function sanitizeData(data: Record<string, unknown>): Record<string, unknown> {
  const sanitize = (value: unknown, depth = 0): unknown => {
    if (depth > 10) return "[max depth]";
    if (typeof value === "string") {
      if (value.startsWith("data:image") || value.startsWith("data:video")) {
        return value.slice(0, 50) + "...[truncated]";
      }
      if (value.length > 300) {
        return value.slice(0, 150) + `...[${value.length} chars]`;
      }
      return value;
    }
    if (Array.isArray(value)) return value.slice(0, 50).map((v) => sanitize(v, depth + 1));
    if (value && typeof value === "object") {
      const entries = Object.entries(value as Record<string, unknown>).slice(0, 50);
      return Object.fromEntries(entries.map(([k, v]) => [k, sanitize(v, depth + 1)]));
    }
    return value;
  };
  return sanitize(data) as Record<string, unknown>;
}

function sendLog(layer: TraceLayer, fn: string, msg: string, data?: Record<string, unknown>, scope?: string): void {
  if (!enabled) return;

  const traceId = getTraceId(scope);
  if (!isTraceIdEnabled(traceId)) return;

  const spanId = generateSpanId();
  const sanitizedData = sanitizeData(data ?? {});

  const log: TraceLog = {
    ts: formatTime(),
    layer,
    fn,
    msg,
    data: sanitizedData,
    traceId,
    spanId,
    scope,
  };

  // 打印到控制台（按 layer 着色）
  const colors: Record<string, string> = {
    "FE-ACTION": "color:#4CAF50;font-weight:bold",
    "FE-API": "color:#2196F3;font-weight:bold",
    "FE-WS": "color:#9C27B0;font-weight:bold",
    "FE-UI": "color:#FF9800;font-weight:bold",
  };
  const style = colors[layer] ?? "";
  console.log(`%c[${log.ts}][${layer}][${fn}] ${msg}`, style, sanitizedData);

  // 通过 Vite 中间件写入文件
  if (import.meta.env.DEV) {
    fetch("/__debug_log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(log),
    }).catch(() => {});
  }
}

// ============================================================================
// 自动点击监听与捕获（初始化时挂上，用户无需手动埋点）
// ============================================================================
let clickTrackerReady = false;

function initClickTracker(): void {
  if (clickTrackerReady) return;
  clickTrackerReady = true;

  document.addEventListener(
    "click",
    (e) => {
      const target = e.target as HTMLElement;
      if (!target || !target.tagName) return;

      // 跳过空标签和特殊标签
      const tag = target.tagName.toLowerCase();
      if (
        ["html", "body", "svg", "path", "g", "rect", "circle"].includes(tag)
      ) {
        return;
      }

      const text = (target.innerText || target.textContent || "").trim();
      const id = target.id ? `#${target.id}` : "";
      const cls = target.className
        ? `.${[...target.classList].join(".")}`
        : "";

      trace.action(
        "click",
        `用户点击 ${tag}${id || cls || ""}`,
        { text, x: e.clientX, y: e.clientY }
      );
    },
    { capture: true }
  );

  console.log("[DebugTracer] 点击监听与捕获已启用（捕获阶段）");
}

// ============================================================================
// 公开 API
// ============================================================================
export const trace = {
  enable(): void {
    enabled = true;
    console.log("[DebugTracer] 已启用");
  },

  disable(): void {
    enabled = false;
    console.log("[DebugTracer] 已禁用");
  },

  isEnabled(): boolean {
    return enabled;
  },

  // --- Scope 追踪 ---
  startScope(scope: string): string {
    const id = `${scope}-${Date.now().toString().slice(-6)}-${Math.random().toString(36).slice(2, 5)}`;
    activeTraces.set(scope, { id, startTime: Date.now() });
    this.action("DebugTracer:startScope", `开始追踪: ${scope}`, { scope, traceId: id });
    return id;
  },

  endScope(scope: string): void {
    const info = activeTraces.get(scope);
    if (info) {
      const duration = Date.now() - info.startTime;
      this.action("DebugTracer:endScope", `结束追踪: ${scope}`, { scope, duration });
      activeTraces.delete(scope);
    }
  },

  getTraceId(scope: string): string | undefined {
    return activeTraces.get(scope)?.id;
  },

  getActiveScopes(): string[] {
    return Array.from(activeTraces.keys());
  },

  // --- Scope 开关 ---
  enableScope(scope: string): void {
    enabledScopes.delete("*");
    enabledScopes.add(scope);
    console.log(`[DebugTracer] Scope 已启用: ${scope}`);
  },

  disableScope(scope: string): void {
    enabledScopes.delete(scope);
    console.log(`[DebugTracer] Scope 已禁用: ${scope}`);
  },

  enableAllScopes(): void {
    enabledScopes = new Set(["*"]);
    console.log("[DebugTracer] 所有 Scope 已启用");
  },

  disableAllScopes(): void {
    enabledScopes = new Set();
    console.log("[DebugTracer] 所有 Scope 已禁用");
  },

  getEnabledScopes(): string[] {
    return Array.from(enabledScopes);
  },

  // --- 日志方法 ---
  action(fn: string, msg: string, data?: Record<string, unknown>): void {
    sendLog("FE-ACTION", fn, msg, data);
  },

  api(fn: string, msg: string, data?: Record<string, unknown>): void {
    sendLog("FE-API", fn, msg, data);
  },

  ws(fn: string, msg: string, data?: Record<string, unknown>): void {
    sendLog("FE-WS", fn, msg, data);
  },

  ui(fn: string, msg: string, data?: Record<string, unknown>): void {
    sendLog("FE-UI", fn, msg, data);
  },

  // --- 工具 ---
  clear(): void {
    spanCounter = 0;
    activeTraces.clear();
    console.log("[DebugTracer] 日志已清空");
  },
};

// 全局挂载（控制台调试用）
if (typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).__trace = trace;
}

// ============================================================================
// 自动初始化（仅开发环境）
// ============================================================================
if (import.meta.env.DEV) {
  // 延迟初始化，等 Vue 挂载完成
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initClickTracker, { once: true });
  } else {
    initClickTracker();
  }

  console.log(
    "%c[Boss DebugTracer] 就绪\n" +
      "  __trace.enable()           - 启用调试\n" +
      "  __trace.disable()          - 禁用调试\n" +
      "  __trace.enableScope(s)     - 启用单个 Scope\n" +
      "  __trace.disableAllScopes() - 禁用所有（需手动开启）\n" +
      "  __trace.enableAllScopes()  - 全开\n" +
      "  __trace.action(fn,msg,data) - 手动记录动作\n" +
      "  __trace.api(fn,msg,data)   - 手动记录 API\n" +
      "  __trace.clear()            - 清空内存日志",
    "color:#4CAF50;font-weight:bold"
  );
}
