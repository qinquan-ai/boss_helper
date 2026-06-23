<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useEngine } from "@/stores/engine";
import { useTheme } from "@/ui/theme";
import ConfigPanel from "@/components/ConfigPanel.vue";
import CollapsedConfigPanel from "@/components/CollapsedConfigPanel.vue";
import ControlBar from "@/components/ControlBar.vue";
import LogConsole from "@/components/LogConsole.vue";
import ResultTable from "@/components/ResultTable";
import ActionDialog from "@/components/ActionDialog.vue";
import Showcase from "@/components/Showcase.vue";
import { Panel, PanelGroup, PanelResizeHandle } from "vue-resizable-panels";

const engine = useEngine();
const { mode, toggle } = useTheme();
const isDev = import.meta.env.DEV;
const tab = ref<"logs" | "results" | "ui">("logs");

// 是否折叠配置面板（由 Panel 的 collapsible 事件驱动）
const configCollapsed = ref(false);

// 根据视口宽度计算初始比例，小屏更窄、大屏稍宽
const getDefaultSize = (): number => {
  const w = window.innerWidth;
  if (w < 1024) return 38;
  if (w < 1280) return 32;
  return 28;
};

onMounted(async () => {
  await engine.loadConfig();
  engine.connectWs();
  if (engine.running) engine.state = "running";
});
</script>

<template>
  <div class="h-screen flex flex-col">
    <header class="flex items-center gap-3 px-6 py-3.5 border-b border-bg-border bg-bg-panel">
      <div class="w-8 h-8 rounded-xl bg-bg-raised border border-bg-border flex items-center justify-center text-fg font-bold">B</div>
      <div>
        <h1 class="text-base font-semibold text-fg leading-tight">BOSS 直聘助手</h1>
        <p class="text-[11px] text-fg-subtle leading-tight">零驱动 · 安全模式 · V14 引擎</p>
      </div>
      <div class="flex-1"></div>
      <button
        class="text-[12px] px-3 py-1.5 rounded-full border border-bg-border text-fg-muted hover:text-fg transition-colors"
        @click="toggle"
      >
        {{ mode === "light" ? "深色" : "浅色" }}
      </button>
      <span
        class="text-[11px] px-2.5 py-1 rounded-full"
        :class="engine.wsConnected ? 'bg-emerald-500/15 text-emerald-500' : 'bg-bg-raised text-fg-subtle'"
      >
        {{ engine.wsConnected ? "● 已连接" : "○ 未连接" }}
      </span>
    </header>

    <main class="flex-1 min-h-0 overflow-hidden">
      <PanelGroup direction="horizontal" auto-save-id="boss:layout" class="flex h-full w-full">
        <!-- 配置面板（可折叠） -->
        <Panel
          v-if="!configCollapsed"
          collapsible
          :default-size="getDefaultSize()"
          :min-size="10"
          :max-size="50"
          class="flex flex-col overflow-hidden"
          @collapse="configCollapsed = true"
        >
          <ConfigPanel class="h-full" @collapse="configCollapsed = true" />
        </Panel>

        <!-- 折叠状态下的窄栏（固定 5%，不折叠） -->
        <Panel
          v-else
          :default-size="5"
          :min-size="5"
          :max-size="5"
          class="flex flex-col overflow-hidden"
        >
          <CollapsedConfigPanel class="h-full" @expand="configCollapsed = false" />
        </Panel>

        <!-- 拖拽手柄：配置面板展开时显示，折叠时隐藏 -->
        <PanelResizeHandle
          v-if="!configCollapsed"
          class="group relative flex w-2 items-center justify-center hover:bg-brand/10 transition-colors cursor-col-resize"
        >
          <div class="flex h-10 w-1 rounded-full bg-border group-hover:bg-brand/50 transition-colors" />
        </PanelResizeHandle>

        <!-- 右侧主内容区 -->
        <Panel :min-size="30" class="flex flex-col overflow-hidden">
          <section class="flex flex-col gap-4 min-w-0 p-4 overflow-y-auto h-full">
            <ControlBar />

            <div class="flex gap-1 bg-bg-panel border border-bg-border rounded-xl p-1 w-fit">
              <button
                class="px-4 py-1.5 rounded-lg text-sm transition-colors"
                :class="tab === 'logs' ? 'bg-brand text-bg-base font-medium' : 'text-fg-muted hover:text-fg'"
                @click="tab = 'logs'"
              >实时日志</button>
              <button
                class="px-4 py-1.5 rounded-lg text-sm transition-colors"
                :class="tab === 'results' ? 'bg-brand text-bg-base font-medium' : 'text-fg-muted hover:text-fg'"
                @click="tab = 'results'; engine.loadResults()"
              >岗位列表</button>
              <button
                v-if="isDev"
                class="px-4 py-1.5 rounded-lg text-sm transition-colors"
                :class="tab === 'ui' ? 'bg-brand text-bg-base font-medium' : 'text-fg-muted hover:text-fg'"
                @click="tab = 'ui'"
              >组件预览</button>
            </div>

            <div class="min-h-[480px]">
              <LogConsole v-show="tab === 'logs'" />
              <ResultTable v-show="tab === 'results'" />
              <Showcase v-if="isDev" v-show="tab === 'ui'" />
            </div>
          </section>
        </Panel>
      </PanelGroup>
    </main>

    <ActionDialog />
  </div>
</template>
