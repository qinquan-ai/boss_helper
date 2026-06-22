import os
import time
import subprocess
import requests
import random
import json
import websocket
from src.config import CONFIG


class StopError(Exception):
    """表示分析被外部要求停止（Ctrl+C 或前端停止按钮），不等 CDP 超时直接放弃。"""
    pass


class BrowserManager:
    def __init__(self, config=None):
        self.config = config or CONFIG
        self.port = None
        self.proc = None
        self.ws = None
        self._owns_browser = False

    @staticmethod
    def quick_connect(browser_type="chrome"):
        """一键连接：供测试脚本使用，自动完成所有初始化"""
        from src.config import get_config
        config = get_config(browser_type)
        bm = BrowserManager(config=config)

        if not bm.try_connect_existing():
            print(f"[-] 未找到活跃的 {browser_type} 浏览器")
            return None

        page = bm.find_boss_page()
        if not page:
            print("[-] 浏览器已连接，但未找到 BOSS 直聘页面")
            return None

        if not bm.connect_ws(page["webSocketDebuggerUrl"]):
            print("[-] WebSocket 连接失败")
            return None

        print(f"[+] 成功快连到 {browser_type} | 页面: {page['url'][:50]}...")
        return bm

    def try_connect_existing(self):
        """尝试连接已有的浏览器实例"""
        port_file = self.config.get("port_file", ".cdp_port")

        if os.path.exists(port_file):
            try:
                with open(port_file, "r") as f:
                    saved_port = int(f.read().strip())
                r = requests.get(f"http://127.0.0.1:{saved_port}/json/version", timeout=2)
                if r.ok:
                    self.port = saved_port
                    print(f"   [+] reusing browser on port {self.port}")
                    return True
            except:
                pass

        # 扫描标准调试端口
        for port in range(9222, 9230):
            try:
                r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=0.5)
                if r.ok:
                    self.port = port
                    print(f"   [+] found browser on port {self.port}")
                    return True
            except:
                pass

        return False

    def launch(self, start_url=None):
        """启动浏览器（免 WebDriver 模式）"""
        self.port = random.randint(40000, 59999)
        browser_path = self.config.get("browser_path")
        if not browser_path or not os.path.exists(browser_path):
            print(f"   [!] 错误: 未找到浏览器可执行文件: {browser_path}")
            return False

        # 标准 CDP 调试启动参数
        args = [
            browser_path,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.config['profile_dir']}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--window-size=1280,720",
        ]
        if start_url:
            args.append(start_url)

        self.proc = subprocess.Popen(args)
        self._owns_browser = True
        print(f"   Browser PID: {self.proc.pid}, port: {self.port}")

        ok = self._wait_for_cdp()
        if ok:
            self._save_port()
        return ok

    def _wait_for_cdp(self):
        for _ in range(15):
            try:
                r = requests.get(f"http://127.0.0.1:{self.port}/json/version", timeout=1)
                if r.ok:
                    return True
            except:
                pass
            time.sleep(1)
        return False

    def _save_port(self):
        port_file = self.config.get("port_file", ".cdp_port")
        try:
            with open(port_file, "w") as f:
                f.write(str(self.port))
        except:
            pass

    def find_boss_page(self):
        """通过 HTTP GET /json 找到 BOSS 直聘标签页。

        优先级：可见的 geek 招聘页 > 任意 zhipin 普通页 > 任意 zhipin 目标。
        登录后浏览器常新开/切换标签页，这里挑"最像在用"的那个，避免连到失效目标。
        """
        pages = self.find_boss_pages()
        if not pages:
            return None

        def score(p):
            url = p.get("url", "")
            s = 0
            if p.get("type") == "page":
                s += 10
            if "/web/geek/" in url:
                s += 5
            if "jobs" in url:
                s += 2
            if "login" in url or "/web/user" in url:
                s -= 8
            return s

        pages.sort(key=score, reverse=True)
        return pages[0]

    def find_boss_pages(self):
        """返回全部 zhipin.com 标签页（type=page 优先），用于多标签场景。"""
        try:
            r = requests.get(f"http://127.0.0.1:{self.port}/json", timeout=3)
            return [p for p in r.json() if "zhipin.com" in p.get("url", "")]
        except Exception:
            return []

    def connect_ws(self, ws_url):
        """连接 WebSocket（不 enable 任何 Domain）"""
        self.ws = websocket.create_connection(ws_url, timeout=15)
        self.ws.sock.settimeout(None)
        return self.ws is not None

    def evaluate(self, expression, await_promise=False, timeout=30):
        """发送 Runtime.evaluate -- 唯一使用的 CDP 命令"""
        return self.send_cdp("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise
        }, timeout=timeout)

    def send_cdp(self, method, params=None, timeout=30, stop_check=None):
        """发送一条 CDP 命令并等待匹配 id 的响应。

        带整体超时：页面跳转/登录重定向时，目标可能被销毁重建，原命令的响应
        会永远不来；若不设超时，recv() 会无限阻塞，导致整条分析线程冻结
        （现象：日志停更、按钮卡在「停止」、页面停在中转 URL）。超时后抛出
        TimeoutError，由调用方按"取数失败"降级处理（重连/重导航）。

        stop_check: 可选回调，类型 ()->bool。
        每 recv() 片（最多 2 秒）调用一次；返回 True 则抛出 StopError 放弃当前
        命令，让分析线程有机会响应 Ctrl+C / 前端停止按钮。
        """
        cmd_id = random.randint(1000, 9999)
        cmd = {
            "id": cmd_id,
            "method": method,
            "params": params or {}
        }
        self.ws.send(json.dumps(cmd))
        deadline = time.time() + timeout if timeout else None
        chunk_timeout = 2.0
        try:
            while True:
                if deadline is not None:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise TimeoutError(f"CDP {method} 响应超时")
                    chunk_timeout = min(chunk_timeout, remaining)
                # 默认用 self.should_stop（由 collector 注入），没有则允许继续
                if stop_check is None:
                    _cb = getattr(self, "should_stop", None)
                    stop_check = _cb if _cb is not None else lambda: False
                if stop_check():
                    raise StopError(f"CDP {method} 被停止")
                try:
                    self.ws.sock.settimeout(chunk_timeout)
                    raw = self.ws.recv()
                except StopError:
                    raise
                except TimeoutError:
                    continue
                except Exception as exc:
                    if deadline is not None and time.time() >= deadline:
                        raise TimeoutError(f"CDP {method} 响应超时") from exc
                    raise
                result = json.loads(raw)
                if result.get("id") == cmd_id:
                    return result
        finally:
            try:
                self.ws.sock.settimeout(None)
            except Exception:
                pass

    def native_click(self, x, y):
        """通过 CDP Input domain 发送设备级鼠标事件"""
        self.send_cdp("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x, "y": y
        })
        time.sleep(random.uniform(0.02, 0.05))
        self.send_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x, "y": y,
            "button": "left",
            "clickCount": 1
        })
        time.sleep(random.uniform(0.01, 0.08))
        self.send_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x, "y": y,
            "button": "left",
            "clickCount": 1
        })

    def get_value(self, result):
        """从 CDP 响应中提取 value，字符串自动 json.loads"""
        raw = result.get("result", {}).get("result", {})
        if isinstance(raw, dict):
            if raw.get("type") == "string":
                try:
                    return json.loads(raw.get("value", "{}"))
                except json.JSONDecodeError:
                    return raw.get("value", {})
            return raw
        return raw

    def disconnect(self):
        """只断开 WebSocket，不关闭 Chrome"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None

    def close(self):
        self.disconnect()
        if self.proc and self._owns_browser:
            try:
                self.proc.kill()
            except:
                pass


ChromeManager = BrowserManager
