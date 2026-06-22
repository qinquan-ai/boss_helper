"""单任务会话管理：同一时间只允许一个分析任务在工作线程中运行。"""
import threading

from src.control import GuiController
from src.collector import run_collection

from .debug_tracer import debug_tracer


class Session:
    def __init__(self):
        self.controller: GuiController | None = None
        self.thread: threading.Thread | None = None
        self.last_params: dict | None = None

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, params: dict):
        if self.running:
            raise RuntimeError("已有任务在运行")
        self.last_params = params
        self.controller = GuiController()
        ctrl = self.controller

        def _run():
            try:
                debug_tracer.entry("session.py:_run", "分析线程开始", {"query": params.get("query")}, scope="collect-start")
                run_collection(controller=ctrl, **params)
            except Exception as exc:  # noqa: BLE001
                debug_tracer.entry("session.py:_run", "分析线程异常", {"error": str(exc)}, scope="error")
                ctrl.log(f"[ERROR] 分析线程异常: {exc}", level="error")
                ctrl.status("error", str(exc))
            finally:
                debug_tracer.end_scope("collect-start")

        self.thread = threading.Thread(target=_run, name="helper_session", daemon=True)
        self.thread.start()

    def stop(self):
        if self.controller:
            debug_tracer.entry("session.py:stop", "停止运行", {}, scope="collect-stop")
            self.controller.request_stop()

    def ack(self, payload: str = ""):
        if self.controller:
            self.controller.ack_user(payload)


session = Session()
