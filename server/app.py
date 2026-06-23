"""FastAPI 后端：REST 控制接口 + WebSocket 实时事件流 + 静态前端托管。"""
import asyncio
import glob
import json
import os
import pathlib

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import get_config, save_config
from src.core.cities import get_cities, refresh_from_browser


from .session import session
from .debug_tracer import debug_tracer

app = FastAPI(title="BOSS 直聘助手 GUI")

# 开发期前端跑在 Vite (5173)，放开跨域便于联调
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartParams(BaseModel):
    count: int = 20
    browser_type: str = "chrome"
    new_chrome: bool = False
    tag: str | None = None
    # 以下字段保留但不再由前端发起（默认关闭关键词路线）
    keyword_search: bool = False
    query: str = ""
    city_code: str | None = None
    city_name: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    tag_sync: bool = False
    safe_mode: bool = True
    fast: bool = False


class AckBody(BaseModel):
    payload: str = ""


class ConfigBody(BaseModel):
    browser_type: str = "chrome"
    browser_path: str | None = None
    output_dir: str | None = None


def _dump(model: BaseModel) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


@app.get("/api/config")
def api_config(browser_type: str = "chrome"):
    cfg = get_config(browser_type)
    return {
        "browser_path": cfg.get("browser_path", ""),
        "profile_dir": cfg.get("profile_dir", ""),
        "output_dir": cfg.get("output_dir", ""),
        "humanize": cfg.get("humanize", {}),
        "running": session.running,
    }


@app.post("/api/config")
def api_save_config(body: ConfigBody):
    """写回 config.yaml（浏览器路径 / 输出目录），返回最新配置。"""
    save_config(
        body.browser_type,
        browser_path=body.browser_path,
        output_dir=body.output_dir,
    )
    cfg = get_config(body.browser_type)
    return {
        "ok": True,
        "browser_path": cfg.get("browser_path", ""),
        "output_dir": cfg.get("output_dir", ""),
    }


@app.get("/api/cities")
def api_get_cities():
    """返回城市列表（内置常用城市，缓存优先）。"""
    return {"cities": get_cities()}


@app.post("/api/cities/refresh")
def api_refresh_cities(browser_type: str = "chrome"):
    """基于已登录的浏览器获取完整城市列表，缓存后返回。"""
    cities, error = refresh_from_browser(browser_type)
    if error:
        return {"ok": False, "error": error, "cities": get_cities()}
    return {"ok": True, "cities": cities}


@app.post("/api/start")
def api_start(params: StartParams):
# 手动模式：用户已在浏览器里做完搜索/筛选，不在这里重复校验
    if session.running:
        return {"ok": False, "error": "已有任务在运行"}
    trace_id = debug_tracer.start_scope("collect-start")
    debug_tracer.entry("app.py:api_start", "分析任务启动", params.model_dump(), scope="collect-start")
    session.start(_dump(params))
    return {"ok": True}


@app.post("/api/stop")
def api_stop():
    session.stop()
    return {"ok": True}


@app.post("/api/pause")
def api_pause():
    session.pause()
    return {"ok": True}


@app.post("/api/resume")
def api_resume():
    session.resume()
    return {"ok": True}


@app.post("/api/ack")
def api_ack(body: AckBody):
    session.ack(body.payload)
    return {"ok": True}


@app.get("/api/status")
def api_status():
    ctrl = session.controller
    return {
        "running": session.running,
        "state": ctrl.state if ctrl else "idle",
        "progress": ctrl.latest_progress if ctrl else {"done": 0, "total": 0, "stats": {}},
        "pending_action": ctrl.pending_action if ctrl else None,
    }


@app.get("/api/results")
def api_results(date: str | None = None):
    cfg = get_config("chrome")
    out = cfg.get("output_dir", "")
    files = sorted(glob.glob(os.path.join(out, "jobs_*.json")), reverse=True)
    if not files:
        return {"jobs": [], "file": None, "files": []}
    target = files[0]
    if date:
        for f in files:
            if date in os.path.basename(f):
                target = f
                break
    try:
        with open(target, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except Exception:
        jobs = []
    return {
        "jobs": jobs,
        "file": os.path.basename(target),
        "files": [os.path.basename(x) for x in files],
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # 连接时先推送当前快照，便于前端刷新后恢复状态
    ctrl = session.controller
    if ctrl:
        await ws.send_json({"type": "status", "state": ctrl.state})
        await ws.send_json({"type": "progress", **ctrl.latest_progress})
        if ctrl.pending_action:
            await ws.send_json({"type": "need_action", **ctrl.pending_action})
    try:
        while True:
            ctrl = session.controller
            if ctrl:
                for ev in ctrl.drain():
                    await ws.send_json(ev)
            await asyncio.sleep(0.15)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.post("/__debug_log")
async def api_debug_log(request: Request):
    """Vite 中间件端点：接收前端日志并写入 .cursor/debug.log + .RandP/debug.log"""
    try:
        body = await request.json()
        debug_tracer.internal("app.py:__debug_log", "前端日志", body)
    except Exception:
        pass
    return {"ok": True}


@app.get("/api/debug/status")
def api_debug_status():
    """返回调试追踪器状态"""
    return {
        "enabled": debug_tracer.is_enabled(),
        "scopes": debug_tracer.get_enabled_scopes(),
        "active": list(debug_tracer.get_enabled_scopes()),
    }


@app.delete("/__debug_log")
def api_debug_clear():
    """清空日志文件"""
    debug_tracer.clear()
    debug_tracer.reset_files()
    return {"ok": True}


@app.get("/__debug_log")
def api_debug_read():
    """读取日志文件内容（供调试面板使用）"""
    log_path = debug_tracer._log_path
    try:
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""


class ScopesBody(BaseModel):
    scopes: list


class EnableBody(BaseModel):
    enabled: bool


@app.post("/api/debug/scopes")
def api_debug_set_scopes(body: ScopesBody):
    """设置启用的 Scope 列表"""
    scopes = set(body.scopes)
    debug_tracer.enable_all_scopes()  # reset first
    if "*" in scopes:
        pass  # all enabled
    else:
        debug_tracer.disable_all_scopes()
        for s in scopes:
            debug_tracer.enable_scope(s)
    return {"ok": True}


@app.post("/api/debug/enable")
def api_debug_set_enable(body: EnableBody):
    """设置全局开关"""
    debug_tracer.set_enabled(body.enabled)
    return {"ok": True}


@app.get("/__debug_panel")
def api_debug_panel():
    """返回调试面板 HTML"""
    panel_path = pathlib.Path(__file__).resolve().parents[1] / "webui" / "public" / "__debug_panel.html"
    try:
        with open(panel_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse(content="<h1>Panel not found</h1>", status_code=404)


# 生产模式：托管前端构建产物（webui/dist 复制到 server/static）
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
