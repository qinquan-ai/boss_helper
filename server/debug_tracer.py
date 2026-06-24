"""
Boss 助手调试追踪器

统一写入本地文件（.cursor/debug.log，NDJSON 格式）和（.RandP/debug.log，人类可读格式）。
用于 boss 前后端调试日志的统一入口。

Layer:
    BE-ENTRY   - API 入口函数
    BE-INTERNAL - 内部函数调用
    BE-WS     - WebSocket 推送

Scope（boss 专用）:
    collect-start - 分析任务启动链路
    collect-stop - 分析任务停止链路
    ws-event    - WebSocket 消息链路
    error       - 错误链路

使用方法:
    from server.debug_tracer import debug_tracer

    # 开始追踪
    trace_id = debug_tracer.start_scope('collect-start')

    # API 入口
    debug_tracer.entry('app.py:api_start', '分析开始', {'query': 'Python'}, scope='collect-start')

    # 内部函数
    debug_tracer.internal('control.py:status', '状态更新', {'state': 'running'}, scope='collect-start')

    # WebSocket 推送
    debug_tracer.ws('app.py:ws_endpoint', '推送进度', {'done': 5}, scope='ws-event')

    # 结束追踪
    debug_tracer.end_scope('collect-start')

Scope 级别开关:
    debug_tracer.enable_scope('collect-start')    # 启用单个 Scope
    debug_tracer.disable_scope('collect-start')   # 禁用单个 Scope
    debug_tracer.enable_all_scopes()             # 全部启用（设为 '*'）
    debug_tracer.disable_all_scopes()            # 全部禁用（需手动开启）
"""
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional


class DebugTracer:
    """Boss 助手调试追踪器单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 默认开启
        env_disabled = os.getenv("DEBUG_TRACE", "").lower()
        self._enabled = env_disabled not in ("false", "0", "no")

        self._project_root = Path(__file__).resolve().parents[1]
        self._log_path = self._project_root / ".cursor" / "debug.log"
        self._readable_path = self._project_root / ".RandP" / "debug.log"

        self._trace_id: Optional[str] = None
        self._span_counter = 0
        self._logs: list = []

        # Scope 级别控制
        scopes_str = os.getenv("DEBUG_TRACE_SCOPES", "*")
        if scopes_str == "*":
            self._enabled_scopes: set = {"*"}
        else:
            self._enabled_scopes = set(s.strip() for s in scopes_str.split(",") if s.strip())

        self._active_traces: Dict[str, Dict[str, Any]] = {}  # scope -> {id, start_time}

        # 确保目录存在
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._readable_path.parent.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 全局开关
    # =========================================================================

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    # =========================================================================
    # Scope 追踪
    # =========================================================================

    def start_scope(self, scope: str, custom_id: Optional[str] = None) -> str:
        """
        开始一个新的 Scope 追踪会话

        Args:
            scope: 业务域 (如: 'collect-start', 'ws-event')
            custom_id: 自定义 ID (可选)

        Returns:
            trace_id (格式: scope-timestamp6位-random3位)
        """
        ts_suffix = str(int(time.time() * 1000))[-6:]
        rand_suffix = os.urandom(2).hex()[:3]
        trace_id = custom_id or f"{scope}-{ts_suffix}-{rand_suffix}"

        self._active_traces[scope] = {
            "id": trace_id,
            "start_time": time.time(),
        }

        if self._is_scope_enabled(scope):
            self._print("BE-ENTRY", "DebugTracer:start_scope", f"开始追踪: {scope}", {"scope": scope, "traceId": trace_id})

        return trace_id

    def end_scope(self, scope: str) -> Optional[int]:
        """
        结束一个 Scope 追踪会话

        Returns:
            duration_ms: 持续时间（毫秒）
        """
        trace_info = self._active_traces.pop(scope, None)
        if trace_info:
            duration = int((time.time() - trace_info["start_time"]) * 1000)
            if self._is_scope_enabled(scope):
                self._print("BE-ENTRY", "DebugTracer:end_scope", f"结束追踪: {scope}", {"scope": scope, "duration": duration})
            return duration
        return None

    def get_trace_id(self, scope: str) -> Optional[str]:
        """获取指定 Scope 的 Trace ID"""
        trace_info = self._active_traces.get(scope)
        return trace_info["id"] if trace_info else None

    # =========================================================================
    # Scope 开关
    # =========================================================================

    def enable_scope(self, scope: str):
        """启用指定 Scope"""
        self._enabled_scopes.discard("*")
        self._enabled_scopes.add(scope)

    def disable_scope(self, scope: str):
        """禁用指定 Scope"""
        self._enabled_scopes.discard(scope)

    def enable_all_scopes(self):
        """启用所有 Scope"""
        self._enabled_scopes = {"*"}

    def disable_all_scopes(self):
        """禁用所有 Scope"""
        self._enabled_scopes = set()

    def is_scope_enabled(self, scope: str) -> bool:
        """检查 Scope 是否启用"""
        return self._is_scope_enabled(scope)

    def get_enabled_scopes(self) -> list:
        """获取当前启用的 Scope 列表"""
        return list(self._enabled_scopes)

    def _is_scope_enabled(self, scope: str) -> bool:
        """检查 Scope 是否启用（内部方法）"""
        if not self._enabled:
            return False
        if "*" in self._enabled_scopes:
            return True
        return scope in self._enabled_scopes

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _generate_span_id(self) -> str:
        self._span_counter += 1
        return f"span-{self._span_counter}"

    def _format_timestamp(self, ts: float) -> str:
        """格式化时间戳为 [HH:mm:ss.SSS] 格式"""
        from datetime import datetime

        dt = datetime.fromtimestamp(ts / 1000) if ts > 1e12 else datetime.fromtimestamp(ts)
        return f"[{dt.strftime('%H:%M:%S')}.{dt.microsecond // 1000:03d}]"

    def _format_timestamp_now(self) -> str:
        """格式化当前时间戳"""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _sanitize_data(self, data: Optional[Dict]) -> Dict:
        """清理数据，截断 base64 字符串和过长字符串"""
        if not data:
            return {}

        def sanitize_value(value: Any, depth: int = 0) -> Any:
            if depth > 10:
                return "[max depth]"

            if isinstance(value, str):
                # 截断 base64 data URL
                if value.startswith("data:image") or value.startswith("data:video"):
                    match = re.match(r"^(data:[^;]+;base64,)(.{20})", value)
                    if match:
                        return f"{match.group(1)}{match.group(2)}...[truncated]"
                    return value[:50] + "...[truncated]"
                # 截断过长字符串
                if len(value) > 300:
                    return value[:150] + f"...[{len(value)} chars]"
                return value

            if isinstance(value, list):
                return [sanitize_value(item, depth + 1) for item in value[:50]]

            if isinstance(value, dict):
                return {k: sanitize_value(v, depth + 1) for k, v in list(value.items())[:50]}

            return value

        return sanitize_value(data)

    def _print(self, layer: str, fn: str, msg: str, data: Optional[Dict] = None):
        """打印到服务器终端"""
        try:
            print(f"[{self._format_timestamp_now()}][{layer}][{fn}] {msg}")
        except UnicodeEncodeError:
            safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
            print(f"[{self._format_timestamp_now()}][{layer}][{fn}] {safe_msg}")
        if data:
            try:
                data_str = str(data)
                if len(data_str) > 500:
                    data_str = data_str[:500] + "..."
                print(f"  {data_str}")
            except UnicodeEncodeError:
                pass

    def _write(self, layer: str, fn: str, msg: str, data: Optional[Dict], scope: Optional[str]):
        """写入日志到文件"""
        timestamp = int(time.time() * 1000)
        time_str = self._format_timestamp(timestamp)
        span_id = self._generate_span_id()
        trace_id = None

        if scope:
            if not self._is_scope_enabled(scope):
                return
            trace_id = self.get_trace_id(scope) or self.start_scope(scope)
        else:
            trace_id = self._trace_id or f"trace-{timestamp}"

        sanitized_data = self._sanitize_data(data)

        log = {
            "ts": time_str,
            "layer": layer,
            "fn": fn,
            "msg": msg,
            "data": sanitized_data,
            "traceId": trace_id,
            "spanId": span_id,
            "scope": scope,
        }

        self._logs.append(log)
        self._print(layer, fn, msg, data)

        # 写入 NDJSON
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # 写入人类可读格式
        try:
            lines = []
            lines.append(f"{time_str} [{layer}] [{fn}]")
            lines.append(f"  > {msg}")
            if data and isinstance(data, dict) and len(data) > 0:
                lines.append("  > data:")
                json_lines = json.dumps(data, ensure_ascii=False, indent=2).split("\n")
                for line in json_lines:
                    lines.append(f"    {line}")
            lines.append("---")
            lines.append("")
            with open(self._readable_path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass

    # =========================================================================
    # 公开 API
    # =========================================================================

    def entry(self, fn: str, msg: str, data: Optional[Dict] = None, scope: Optional[str] = None):
        """记录 API 入口日志 (BE-ENTRY)"""
        self._write("BE-ENTRY", fn, msg, data, scope)

    def internal(self, fn: str, msg: str, data: Optional[Dict] = None, scope: Optional[str] = None):
        """记录内部函数日志 (BE-INTERNAL)"""
        self._write("BE-INTERNAL", fn, msg, data, scope)

    def ws(self, fn: str, msg: str, data: Optional[Dict] = None, scope: Optional[str] = None):
        """记录 WebSocket 推送日志 (BE-WS)"""
        self._write("BE-WS", fn, msg, data, scope)

    def get_logs(self) -> list:
        """获取所有日志"""
        return self._logs.copy()

    def clear(self):
        """清空日志"""
        self._logs = []
        self._trace_id = None
        self._span_counter = 0

    def reset_files(self):
        """清空日志文件"""
        try:
            if self._log_path.exists():
                self._log_path.unlink()
        except Exception:
            pass
        try:
            if self._readable_path.exists():
                self._readable_path.unlink()
        except Exception:
            pass


# 单例实例
debug_tracer = DebugTracer()


# 便捷函数
def start_scope(scope: str, custom_id: Optional[str] = None) -> str:
    return debug_tracer.start_scope(scope, custom_id)


def end_scope(scope: str) -> Optional[int]:
    return debug_tracer.end_scope(scope)


def trace_entry(fn: str, msg: str, data: Optional[Dict] = None, scope: Optional[str] = None):
    return debug_tracer.entry(fn, msg, data, scope)


def trace_internal(fn: str, msg: str, data: Optional[Dict] = None, scope: Optional[str] = None):
    return debug_tracer.internal(fn, msg, data, scope)


def trace_ws(fn: str, msg: str, data: Optional[Dict] = None, scope: Optional[str] = None):
    return debug_tracer.ws(fn, msg, data, scope)
