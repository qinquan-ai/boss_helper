/**
 * Boss 助手前端调试追踪器
 *
 * 直接导出标准 @qin16778/tracelink tracer 单例。
 * 开发环境自动连接 board 接收端 + 自动点击追踪。
 */
import { tracer } from "@qin16778/tracelink";
import { HttpSink } from "@qin16778/tracelink/browser";

// 开发环境：连接 board 接收端
if (import.meta.env.DEV) {
  const sink = new HttpSink({ endpoint: "http://127.0.0.1:5174/__debug_log" });
  tracer.configure({ enabled: true, httpSink: (log) => sink.send(log) });

  // 自动点击追踪
  import("@qin16778/tracelink/browser")
    .then(({ installAutoClick }) => installAutoClick())
    .catch(() => {});

  console.log(
    "%c[TraceLink] 就绪 — window.__trace 可用",
    "color:#4CAF50;font-weight:bold"
  );
}

// 控制台调试入口
if (typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).__trace = tracer;
}

export { tracer as trace };
