<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useEngine } from "@/stores/engine";
import { useTheme } from "@/ui/theme";
import ConfigPanel from "@/components/ConfigPanel.vue";
import CollapsedConfigPanel from "@/components/CollapsedConfigPanel.vue";
import ControlBar from "@/components/ControlBar.vue";
import LogConsole from "@/components/LogConsole.vue";
import ResultTable from "@/components/ResultTable";
import ActionDialog from "@/components/ActionDialog.vue";
import { useLocalStorage } from "@/composables/useLocalStorage";

const engine = useEngine();
const { mode, toggle } = useTheme();
const tab = ref<"logs" | "results">("logs");
const configWidth = useLocalStorage<number>("boss:config-width", 300, {
  validator: (v) => typeof v === "number" && v >= 220 && v<= 500,
});


// ConfigPanel 折叠偏好（跨刷新 / 跨标签同步）
const configCollapsed = useLocalStorage<boolean>(
  "boss:config-collapsed",
  false,
  { validator: (v): v is boolean => typeof v === "boolean" }
);

// 测顶栏实际高度，写入 CSS 变量；sticky 锚点跟着它走
const headerRef = ref<HTMLElement | null>(null);
let ro: ResizeObserver | null = null;
function measureHeader() {
  const el = headerRef.value;
  if (!el) return;
  document.documentElement.style.setProperty("--header-h", `${el.offsetHeight}px`);
}

onMounted(async () => {
  requestAnimationFrame(measureHeader);
  if (typeof ResizeObserver !== "undefined" && headerRef.value) {
    ro = new ResizeObserver(measureHeader);
    ro.observe(headerRef.value);
  }

  await engine.loadConfig();
  engine.connectWs();
  if (engine.running) engine.state = "running";
});

onUnmounted(() => {
  ro?.disconnect();
  ro = null;
});
</script>

<template>
  <div class="h-screen flex flex-col">
    <!-- 顶栏 -->
    <header
      ref="headerRef"
      class="flex items-center gap-3 px-6 py-3.5 border-b border-bg-border bg-bg-panel"
    >
      <div class="w-8 h-8 rounded-xl bg-bg-raised border border-bg-border flex items-center justify-center text-fg font-bold">
        B
      </div>
      <div>
        <h1 class="text-base font-semibold text-fg leading-tight">BOSS 直聘助手</h1>
      </div>
      <div class="flex-1"></div>

      <button
        class="text-[12px] px-3 py-1.5 rounded-full border border-bg-border text-fg-muted hover:text-fg transition-colors"
        :title="mode === 'light' ? '切换到深色' : '切换到浅色'"
        @click="toggle"
      >
        {{ mode === "light" ? "🌙 深色" : "☀️ 浅色" }}
      </button>
      <span
        class="text-[11px] px-2.5 py-1 rounded-full"
        :class="engine.wsConnected ? 'bg-emerald-500/15 text-emerald-500' : 'bg-bg-raised text-fg-subtle'"
      >
        {{ engine.wsConnected ? "● 已连接" : "○ 未连接" }}
      </span>
    </header>

    <!-- 主体：
         - 窄屏：单列纵向堆叠；ConfigPanel 在上、右半边在下；main 整体竖滚
         - 宽屏：ConfigPanel 用 fixed 定位贴视口左边，高 100dvh；main 左侧预留 ConfigPanel 宽度，避免内容被遮挡
    -->
    <main
      class="flex-1 min-h-0 grid grid-cols-1 overflow-y-auto overflow-x-hidden"
      :class="configCollapsed
        ? 'lg:grid-cols-[64px_1fr]'
        : 'lg:grid-cols-[300px_1fr]'"
    >
      <!-- ConfigPanel 列：fixed 定位贴视口左侧，高度 100dvh（包含 header 高度），
           内容从 header 下方开始；展开 300px / 折叠 64px 宽度过渡 -->
      <div class="relative hidden lg:block">
        <div
          class="fixed top-0 left-0 w-full h-screen transition-[width,padding] duration-300 ease-out pointer-events-none"
          :class="configCollapsed
            ? 'lg:w-[64px] lg:pl-0'
            : 'lg:w-[300px] lg:pl-0'"
        >
          <div
            class="h-full pt-[calc(var(--header-h)+1rem)] pb-4 pl-4 pr-0 pointer-events-auto"
          >
            <div class="h-full overflow-hidden">
              <ConfigPanel
                v-if="!configCollapsed"
                class="h-full"
                @collapse="configCollapsed = true"
              />
              <CollapsedConfigPanel
                v-else
                class="h-full"
                @expand="configCollapsed = false"
              />
            </div>
          </div>
        </div>
      </div>

      <section class="flex flex-col gap-4 min-w-0 p-4">
        <ControlBar />

        <div class="flex gap-1 bg-bg-panel border border-bg-border rounded-xl p-1 w-fit">
          <button
            class="px-4 py-1.5 rounded-lg text-sm transition-colors"
            :class="tab === 'logs' ? 'bg-brand text-bg-base font-medium' : 'text-fg-muted hover:text-fg'"
            @click="tab = 'logs'"
          >
            实时日志
          </button>
          <button
            class="px-4 py-1.5 rounded-lg text-sm transition-colors"
            :class="tab === 'results' ? 'bg-brand text-bg-base font-medium' : 'text-fg-muted hover:text-fg'"
            @click="tab = 'results'; engine.loadResults()"
          >
            岗位列表
          </button>
        </div>

        <div class="min-h-[480px]">
          <LogConsole v-show="tab === 'logs'" />
          <ResultTable v-show="tab === 'results'" />
        </div>
      </section>
    </main>

    <ActionDialog />
  </div>
</template>
