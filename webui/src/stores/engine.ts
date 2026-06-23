import { defineStore } from "pinia";
import { api, type City, type EngineConfig, type Job, type StartParams } from "@/api";
import { trace } from "@/utils/debugTracer";

/** 解析薪资文本 → [min, max]（单位 K）。无法解析返回 null。 */
function parseSalary(text?: string): [number, number] | null {
  if (!text) return null;
  const s = String(text);
  if (/\/(天|时|小时)|元\/(天|时|小时)/.test(s)) return null;
  let m = s.match(/(\d+(?:\.\d+)?)\s*[-~―]\s*(\d+(?:\.\d+)?)\s*[Kk]/);
  if (m) return [parseFloat(m[1]), parseFloat(m[2])];
  m = s.match(/(\d+(?:\.\d+)?)\s*万?\s*[-~―]\s*(\d+(?:\.\d+)?)\s*万/);
  if (m) return [parseFloat(m[1]) * 10, parseFloat(m[2]) * 10];
  m = s.match(/(\d+(?:\.\d+)?)\s*千?\s*[-~―]\s*(\d+(?:\.\d+)?)\s*千/);
  if (m) return [parseFloat(m[1]), parseFloat(m[2])];
  m = s.match(/(\d+(?:\.\d+)?)\s*[Kk]/);
  if (m) return [parseFloat(m[1]), parseFloat(m[1])];
  return null;
}

export interface LogEntry {
  id: number;
  level: string;
  msg: string;
}

export interface PendingAction {
  reason: string;
  kind: string;
}

export type EngineState =
  | "idle"
  | "running"
  | "paused"
  | "waiting"
  | "done"
  | "stopped"
  | "error";

interface State {
  config: EngineConfig | null;
  params: StartParams;
  state: EngineState;
  running: boolean;
  progress: { done: number; total: number; stats: Record<string, number> };
  logs: LogEntry[];
  pendingAction: PendingAction | null;
  jobs: Job[];
  resultFiles: string[];
  currentFile: string | null;
  wsConnected: boolean;
  errorMsg: string;
  cities: City[];
  citiesRefreshing: boolean;
  stopping: boolean;
  pausing: boolean;
}

let logSeq = 0;
let ws: WebSocket | null = null;

export const useEngine = defineStore("engine", {
  state: (): State => ({
    config: null,
    params: {
      count: 20,
      browser_type: "chrome",
      safe_mode: true,
      fast: false,
      new_chrome: false,
      tag: null,
      keyword_search: true,
      query: "",
      city_code: null,
      city_name: null,
      salary_min: null,
      salary_max: null,
      tag_sync: false,
    },
    state: "idle",
    running: false,
    progress: { done: 0, total: 0, stats: {} },
    logs: [],
    pendingAction: null,
    jobs: [],
    resultFiles: [],
    currentFile: null,
    wsConnected: false,
    errorMsg: "",
    cities: [],
    citiesRefreshing: false,
    stopping: false,
    pausing: false,
  }),

  getters: {
    percent(s): number {
      if (!s.progress.total) return 0;
      return Math.min(100, Math.round((s.progress.done / s.progress.total) * 100));
    },
    statusLabel(s): string {
      return (
        {
          idle: "空闲",
          running: "运行中",
          paused: "已暂停",
          waiting: "等待操作",
          done: "已完成",
          stopped: "已停止",
          error: "出错",
        } as Record<string, string>
      )[s.state] || s.state;
    },
    canStart(s): boolean {
      if (!s.config) return false;
      if (s.params.keyword_search) return !!(s.params.query || "").trim();
      return true;
    },
  },

  actions: {
    pushLog(level: string, msg: string) {
      this.logs.push({ id: ++logSeq, level, msg });
      if (this.logs.length > 2000) this.logs.splice(0, this.logs.length - 2000);
    },

    async loadConfig() {
      try {
        this.config = await api.getConfig(this.params.browser_type);
        this.running = this.config.running;
      } catch (e) {
        this.pushLog("error", `加载配置失败: ${e}`);
      }
    },

    async start() {
      if (this.params.keyword_search && !(this.params.query || "").trim()) {
        this.errorMsg = "请先输入搜索关键词";
        return;
      }
      this.errorMsg = "";
      this.logs = [];
      this.progress = { done: 0, total: this.params.count, stats: {} };
      trace.startScope("collect-start");
      trace.action("engine:start", "用户点击启动", {
        query: this.params.query,
        city: this.params.city_name,
        count: this.params.count,
      });
      try {
        const r = await api.start(this.params);
        if (!r.ok) {
          this.errorMsg = r.error || "启动失败";
          this.pushLog("error", this.errorMsg);
          trace.action("engine:start", "启动失败", { error: this.errorMsg });
          trace.endScope("collect-start");
          return;
        }
      } catch (e) {
        this.errorMsg = `启动失败: ${e}`;
        this.pushLog("error", this.errorMsg);
        trace.action("engine:start", "启动异常", { error: String(e) });
        trace.endScope("collect-start");
        return;
      }
      this.state = "running";
      this.running = true;
      this.connectWs();
    },

    async loadCities() {
      try {
        const r = await api.getCities();
        this.cities = r.cities || [];
      } catch (e) {
        this.pushLog("error", `加载城市列表失败: ${e}`);
      }
    },

    async refreshCities() {
      this.citiesRefreshing = true;
      try {
        const r = await api.refreshCities(this.params.browser_type);
        this.cities = r.cities || this.cities;
        if (!r.ok) this.pushLog("warn", r.error || "刷新城市列表失败");
        else this.pushLog("info", `城市列表已更新，共 ${this.cities.length} 个`);
      } catch (e) {
        this.pushLog("error", `刷新城市列表失败: ${e}`);
      } finally {
        this.citiesRefreshing = false;
      }
    },

    async saveConfig(patch: { browser_path?: string; output_dir?: string }) {
      try {
        const r = await api.saveConfig({
          browser_type: this.params.browser_type,
          ...patch,
        });
        if (this.config) {
          this.config.browser_path = r.browser_path;
          this.config.output_dir = r.output_dir;
        }
      } catch (e) {
        this.pushLog("error", `保存配置失败: ${e}`);
      }
    },

    async stop() {
      if (this.stopping) return;
      this.stopping = true;
      this.pushLog("warn", "已发送停止指令，等待当前条目收尾 ...");
      trace.startScope("collect-stop");
      trace.action("engine:stop", "用户点击停止", {});
      try {
        await api.stop();
      } catch (e) {
        this.pushLog("error", `停止失败: ${e}`);
        trace.action("engine:stop", "停止失败", { error: String(e) });
      }
      const started = Date.now();
      const poll = async () => {
        if (!this.stopping) return;
        if (Date.now() - started > 60000) {
          this.finishStop();
          return;
        }
        try {
          const s = await api.getStatus();
          if (!s.running) {
            this.finishStop();
            return;
          }
        } catch {
          /* 忽略瞬时网络错误，继续轮询 */
        }
        setTimeout(poll, 800);
      };
      setTimeout(poll, 800);
    },

    async pause() {
      if (this.pausing || this.state !== "running") return;
      this.pausing = true;
      this.pushLog("warn", "已发送暂停指令 ...");
      trace.startScope("collect-pause");
      trace.action("engine:pause", "用户点击暂停", {});
      try {
        await api.pause();
      } catch (e) {
        this.pushLog("error", `暂停失败: ${e}`);
        trace.action("engine:pause", "暂停失败", { error: String(e) });
        this.pausing = false;
      }
    },

    async resume() {
      if (!this.pausing && this.state !== "paused") return;
      this.pausing = false;
      this.pushLog("info", "继续采集 ...");
      trace.startScope("collect-resume");
      trace.action("engine:resume", "用户点击继续", {});
      try {
        await api.resume();
      } catch (e) {
        this.pushLog("error", `继续失败: ${e}`);
        trace.action("engine:resume", "继续失败", { error: String(e) });
      }
    },

    finishStop() {
      this.stopping = false;
      this.pausing = false;
      this.running = false;
      if (this.state === "running" || this.state === "waiting" || this.state === "paused") this.state = "stopped";
      this.pendingAction = null;
      trace.endScope("collect-stop");
      trace.endScope("collect-start");
      trace.endScope("collect-pause");
      trace.endScope("collect-resume");
      this.loadResults();
    },

    async ack(payload = "") {
      await api.ack(payload);
      this.pendingAction = null;
      if (this.running) this.state = "running";
    },

    async loadResults(date?: string) {
      try {
        const r = await api.getResults(date);
        const jobs: Job[] = (r.jobs || []).map((j: any) => {
          if (j.salary && (j.salaryMin == null || j.salaryMax == null)) {
            const parsed = parseSalary(j.salary);
            if (parsed) {
              j.salaryMin = parsed[0];
              j.salaryMax = parsed[1];
            }
          }
          return j as Job;
        });
        this.jobs = jobs;
        this.resultFiles = r.files || [];
        this.currentFile = r.file;
      } catch (e) {
        this.pushLog("error", `加载结果失败: ${e}`);
      }
    },

    connectWs() {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING))
        return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/ws`);
      ws.onopen = () => {
        this.wsConnected = true;
        trace.ws("engine:connectWs", "WebSocket 已连接", {});
      };
      ws.onclose = () => {
        this.wsConnected = false;
        if (this.running) setTimeout(() => this.connectWs(), 1000);
      };
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        trace.ws("engine:handleEvent", `收到 WS 消息: ${data.type}`, data);
        this.handleEvent(data);
      };
    },

    handleEvent(ev: any) {
      switch (ev.type) {
        case "log":
          this.pushLog(ev.level || "info", ev.msg ?? "");
          if (ev.level === "error") {
            trace.action("engine:handleEvent", "引擎日志错误", { msg: ev.msg });
          }
          break;
        case "progress":
          this.progress = {
            done: ev.done ?? 0,
            total: ev.total ?? this.progress.total,
            stats: ev.stats ?? {},
          };
          break;
        case "status":
          this.state = ev.state as EngineState;
          trace.action("engine:handleEvent", `状态变更: ${ev.state}`, { detail: ev.detail });
          if (ev.state === "done" || ev.state === "stopped") {
            this.running = false;
            this.stopping = false;
            this.pausing = false;
            this.loadResults();
          }
          if (ev.state === "error") {
            this.running = false;
            this.stopping = false;
            this.pausing = false;
            if (this.stopping || String(ev.detail ?? "").includes("被停止")) {
              this.state = "stopped";
            }
            this.errorMsg = String(ev.detail ?? "");
            this.loadResults();
          }
          if (ev.state === "paused") {
            this.pausing = false;
          }
          break;
        case "need_action":
          this.pendingAction = { reason: ev.reason, kind: ev.kind || "confirm" };
          this.state = "waiting";
          trace.action("engine:handleEvent", "需要用户操作", { reason: ev.reason, kind: ev.kind });
          break;
      }
    },
  },
});
