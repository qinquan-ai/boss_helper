<script setup lang="ts">
import { computed } from "vue";
import { useEngine } from "@/stores/engine";
import { useLocalStorage } from "@/composables/useLocalStorage";

const engine = useEngine();

const statsCollapsed = useLocalStorage<boolean>(
  "boss:stats-collapsed",
  true,
  { validator: (v): v is boolean => typeof v === "boolean" }
);

const stats = computed(() => engine.progress.stats || {});

const stateColor = computed(
  () =>
    ({
      idle: "bg-fg-subtle",
      running: "bg-brand animate-pulse-ring",
      paused: "bg-amber-500 animate-pulse-ring",
      waiting: "bg-amber-500 animate-pulse-ring",
      done: "bg-emerald-500",
      stopped: "bg-fg-subtle",
      error: "bg-rose-500",
    } as Record<string, string>)[engine.state] || "bg-fg-subtle"
);

const metrics = [
  { k: "success", label: "成功", cls: "text-emerald-500" },
  { k: "fail", label: "失败", cls: "text-rose-500" },
  { k: "skip", label: "跳过", cls: "text-fg-muted" },
  { k: "vue_hit", label: "Vue直读", cls: "text-fg" },
];
</script>

<template>
  <div class="card p-5">
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2.5">
        <span class="w-2.5 h-2.5 rounded-full" :class="stateColor"></span>
        <span class="text-sm font-semibold text-fg">{{ engine.statusLabel }}</span>
        <span
          v-if="!engine.wsConnected && engine.running"
          class="text-[11px] text-amber-500"
          >· 重连中</span
        >
      </div>

      <div class="flex-1"></div>

      <button
        type="button"
        class="w-7 h-7 rounded-full flex items-center justify-center transition-fast bg-white/5 hover:bg-white/10 text-fg-muted hover:text-fg"
        :title="statsCollapsed ? '展开统计' : '折叠统计'"
        :aria-label="statsCollapsed ? '展开统计' : '折叠统计'"
        :aria-expanded="!statsCollapsed"
        @click="statsCollapsed = !statsCollapsed"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          class="transition-transform duration-200"
          :class="statsCollapsed ? 'rotate-180' : ''"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      <!-- 暂停 / 继续（仅运行中可见） -->
      <template v-if="engine.running && engine.state !== 'paused'">
        <button
          v-if="engine.pausing"
          class="btn-ghost opacity-60 cursor-not-allowed"
          disabled
        >
          暂停中…
        </button>
        <button
          v-else
          class="btn-ghost"
          :disabled="!engine.running"
          title="暂停采集，可稍后继续"
          @click="engine.pause()"
        >
          ⏸ 暂停
        </button>
      </template>

      <!-- 继续（暂停时可见） -->
      <button
        v-if="engine.state === 'paused'"
        class="btn-primary"
        title="继续采集"
        @click="engine.resume()"
      >
        ▶ 继续
      </button>

      <!-- 停止（运行中或暂停时可见） -->
      <button
        v-if="engine.running || engine.state === 'paused'"
        class="btn-danger"
        :disabled="engine.stopping"
        :class="{ 'opacity-60 cursor-not-allowed': engine.stopping }"
        @click="engine.stop()"
      >
        {{ engine.stopping ? '■ 停止中…' : '■ 停止' }}
      </button>

      <!-- 启动（仅空闲时可见） -->
      <button
        v-if="!engine.running && engine.state !== 'paused'"
        class="btn-primary"
        :disabled="!engine.canStart"
        :title="
          engine.params.keyword_search && !engine.params.query?.trim()
            ? '请先输入搜索关键词'
            : ''
        "
        @click="engine.start()"
      >
        ▶ 启动助手
      </button>
    </div>

    <!-- 进度条 -->
    <div class="mt-4">
      <div class="flex justify-between text-xs text-fg-muted mb-1.5">
        <span>进度 {{ engine.progress.done }} / {{ engine.progress.total }}</span>
        <span>{{ engine.percent }}%</span>
      </div>
      <div class="h-2 rounded-full bg-bg-raised overflow-hidden">
        <div
          class="h-full bg-brand rounded-full transition-all duration-500"
          :style="{ width: engine.percent + '%' }"
        ></div>
      </div>
    </div>

    <!-- 统计区：可折叠 -->
    <div
      class="grid transition-all duration-300 ease-out"
      :class="statsCollapsed
        ? 'grid-rows-[0fr] opacity-0 mt-0'
        : 'grid-rows-[1fr] opacity-100 mt-4'"
    >
      <div class="overflow-hidden">
        <div class="grid grid-cols-3 sm:grid-cols-6 gap-2">
          <div v-for="m in metrics" :key="m.k" class="tile px-3 py-2 text-center">
            <div class="text-lg font-semibold" :class="m.cls">{{ stats[m.k] || 0 }}</div>
            <div class="text-[11px] text-fg-subtle">{{ m.label }}</div>
          </div>
        </div>
        <p v-if="engine.errorMsg" class="mt-3 text-xs text-rose-500">{{ engine.errorMsg }}</p>
      </div>
    </div>
  </div>
</template>
