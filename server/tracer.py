"""
Boss 助手 TraceLink 追踪入口

直接导出标准 tracelink Python SDK 的 tracer 单例。
开发环境自动连接 Dashboard Receiver。
"""
import os
from tracelink import tracer

# 连接 Dashboard Receiver
receiver_port = os.getenv("TRACELINK_PORT", "5174")
receiver_endpoint = f"http://127.0.0.1:{receiver_port}/__debug_log"
tracer.configure(
    http_endpoint=receiver_endpoint,
    http_timeout_ms=2000,
    scope_sync_endpoint=f"{receiver_endpoint}/scopes",
)
