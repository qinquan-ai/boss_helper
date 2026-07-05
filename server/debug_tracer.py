"""
Boss 助手调试追踪器

直接导出标准 tracelink Python SDK 的 debug_tracer 单例。
开发环境自动连接 board 接收端。
"""
import os
from tracelink import debug_tracer

# 连接 board 接收端
board_port = os.getenv("TRACELINK_PORT", "5174")
debug_tracer.configure(
    http_endpoint=f"http://127.0.0.1:{board_port}/__debug_log",
    http_timeout_ms=2000
)
