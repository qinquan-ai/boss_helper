"""助手引擎控制器抽象。

引擎（collector.run_collection）不再直接 print/input，而是通过 Controller：
  - log()        输出日志
  - progress()   汇报进度与统计
  - status()     汇报运行状态
  - wait_user()  替代 input()，阻塞直到用户放行（返回用户输入文本）
  - should_stop() 循环内检查，支持中途停止

CLI 用 ConsoleController（保持原有 print/input 行为），
GUI 用 GuiController（事件入队 + 线程事件等待，由 FastAPI 桥接到 WebSocket）。

Debug tracing via server.debug_tracer (lazy import to avoid circular imports).
"""
import queue
import threading


class BaseController:
    def log(self, msg="", level="info", end="\n"):
        raise NotImplementedError

    def progress(self, done, total, stats=None):
        pass

    def status(self, state, detail=None):
        pass

    def wait_user(self, reason, kind="confirm"):
        """阻塞等待用户操作，返回用户输入的文本（可为空字符串）。"""
        return ""

    def should_stop(self) -> bool:
        return False


class ConsoleController(BaseController):
    """命令行控制器：保持项目原有的 print / input 行为。"""

    def log(self, msg="", level="info", end="\n"):
        print(msg, end=end, flush=True)

    def wait_user(self, reason, kind="confirm"):
        try:
            return input(reason)
        except EOFError:
            return ""

    def should_stop(self) -> bool:
        return False


class GuiController(BaseController):
    """GUI 控制器：把事件放入线程安全队列，阻塞等待前端 ack/stop。"""

    def __init__(self):
        self.events: "queue.Queue[dict]" = queue.Queue()
        self._stop = threading.Event()
        self._resume = threading.Event()
        self._action_payload = ""
        self.latest_progress = {"done": 0, "total": 0, "stats": {}}
        self.state = "idle"
        self.pending_action = None  # 当前等待中的人工介入 {reason, kind}

    # ---------- 生产者侧：引擎线程调用 ----------
    def log(self, msg="", level="info", end="\n"):
        text = str(msg)
        if not text.strip() and end == "":
            return
        self.events.put({"type": "log", "level": level, "msg": text})
        if level == "error":
            import server.debug_tracer as dt
            dt.debug_tracer.entry("control.py:GuiController.log", "引擎错误", {"msg": text[:200]}, scope="error")

    def progress(self, done, total, stats=None):
        self.latest_progress = {"done": done, "total": total, "stats": stats or {}}
        self.events.put({"type": "progress", "done": done, "total": total, "stats": stats or {}})
        import server.debug_tracer as dt
        dt.debug_tracer.internal("control.py:GuiController.progress", "进度更新", {"done": done, "total": total}, scope="collect-start")

    def status(self, state, detail=None):
        self.state = state
        self.events.put({"type": "status", "state": state, "detail": detail})
        import server.debug_tracer as dt
        dt.debug_tracer.internal("control.py:GuiController.status", f"状态切换: {state}", {"detail": str(detail)[:200] if detail else None}, scope="collect-start")

    def wait_user(self, reason, kind="confirm"):
        self._resume.clear()
        self._action_payload = ""
        self.pending_action = {"reason": reason, "kind": kind}
        self.events.put({"type": "need_action", "reason": reason, "kind": kind})
        # 阻塞直到前端 ack 或请求停止
        while not self._resume.is_set():
            if self._stop.is_set():
                break
            self._resume.wait(0.2)
        self.pending_action = None
        return self._action_payload

    def should_stop(self) -> bool:
        return self._stop.is_set()

    # ---------- 消费者侧：FastAPI 线程调用 ----------
    def request_stop(self):
        self._stop.set()
        self._resume.set()  # 解除任何 wait_user 阻塞

    def ack_user(self, payload=""):
        self._action_payload = payload or ""
        self._resume.set()

    def drain(self):
        """取出当前队列中的全部事件（非阻塞）。"""
        items = []
        while True:
            try:
                items.append(self.events.get_nowait())
            except queue.Empty:
                break
        return items
