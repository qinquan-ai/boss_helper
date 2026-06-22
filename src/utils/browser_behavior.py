import time
import random
import json

from src.core.js_loader import load_js


class BrowserBehavior:
    """浏览器交互行为封装：点击卡片、滚动、间隔延迟。"""

    @staticmethod
    def get_browse_delay():
        dice = random.random()
        if dice < 0.35:
            wait = random.uniform(1.2, 2.8)
        elif dice > 0.85:
            wait = random.uniform(8.0, 15.0)
        else:
            wait = random.uniform(3.2, 6.0)
        return wait

    @staticmethod
    def click_job(chrome, security_id):
        """
        点击目标卡片，Vue clickJobCard() 优先，DOM card.click() 兜底。

        通过 securityId 精确匹配 Vue 组件并点击对应卡片。

        返回 (是否成功, 卡片在页面中的位置索引, 总卡片数)
        """
        sid_e = security_id.replace("\\", "\\\\").replace("'", "\\'")

        # === 方式1: Vue clickJobCard()（优先，与数据读取层一致）===
        vue_js = load_js("click_vue.js", {"'__SID__'": f"'{sid_e}'"})
        r = chrome.evaluate(vue_js, await_promise=True)
        raw = chrome.get_value(r)
        if isinstance(raw, str):
            try:
                info = json.loads(raw or "{}")
            except:
                info = {}
        else:
            info = raw if raw is not None else {}
        if isinstance(info, dict) and info.get("ok"):
            time.sleep(0.5)
            return True, info.get("index", 0), info.get("total", 0)

        # === 方式2: DOM card.click()（兜底）===
        dom_js = load_js("click_dom.js", {"'__SID__'": f"'{sid_e}'"})
        r = chrome.evaluate(dom_js, await_promise=True)
        raw = chrome.get_value(r)
        if isinstance(raw, str):
            info = json.loads(raw or "{}")
        else:
            info = raw if raw is not None else {}
        if info.get("found"):
            time.sleep(0.5)
            return True, info.get("index", 0), info.get("total", 0)

        return False, -1, info.get("total", 0)

    @staticmethod
    def click_card_by_sid(chrome, security_id, job_name):
        """兼容旧接口，内部委托给 click_job"""
        return BrowserBehavior.click_job(chrome, security_id)

    @staticmethod
    def get_scroll_position(chrome):
        """获取当前左侧列表的滚动位置（调试用）"""
        result = chrome.evaluate(load_js("scroll_position.js"))
        raw = chrome.get_value(result)
        if isinstance(raw, str):
            return json.loads(raw or "{}")
        return raw if raw is not None else {}

    @staticmethod
    def scroll_detail(chrome):
        """滚动浏览右侧详情面板"""
        chrome.evaluate(load_js("scroll_detail.js"))

    @staticmethod
    def auto_scroll_list(chrome):
        """列表为空时触发懒加载：向下滚动一段距离，激活 BOSS 原生无限滚动加载"""
        chrome.evaluate(load_js("scroll_list.js"), await_promise=True)
        time.sleep(2.0)

    @staticmethod
    def step_break():
        """每 N 条休息一次"""
        idle = random.uniform(8.0, 18.0)
        print(f"\n  [IDLE] 间隔休息 {idle:.1f}s ...")
        time.sleep(idle)
