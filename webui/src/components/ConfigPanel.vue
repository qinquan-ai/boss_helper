<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useEngine } from "@/stores/engine";
import { GlassSelect, GlassCheckbox, GlassToggle } from "@/ui";

defineEmits<{
  (e: "collapse"): void;
}>();

const engine = useEngine();

const browserOptions = [
  { label: "Chrome", value: "chrome" },
  { label: "Edge", value: "edge" },
];

onMounted(() => {
  if (!engine.cities.length) engine.loadCities();
});

function onBrowserChange(v: string) {
  engine.params.browser_type = v;
  engine.loadConfig();
}

function onCityChange(code: string) {
  engine.params.city_code = code || null;
  const hit = engine.cities.find((c) => c.value === code);
  engine.params.city_name = hit ? hit.label : null;
}

// 是否运行在桌面壳（pywebview 注入 API）；纯浏览器 dev 下回退为手动输入
const hasNativePicker = computed(
  () => typeof (window as any).pywebview?.api?.pick_folder === "function"
);

async function pickFolder() {
  const api = (window as any).pywebview?.api;
  if (!api?.pick_folder) return;
  const p = await api.pick_folder();
  if (p) engine.saveConfig({ output_dir: p });
}

async function pickBrowser() {
  const api = (window as any).pywebview?.api;
  if (!api?.pick_file) return;
  const p = await api.pick_file();
  if (p) engine.saveConfig({ browser_path: p });
}

function onBrowserPathChange(e: Event) {
  engine.saveConfig({ browser_path: (e.target as HTMLInputElement).value });
}
function onOutputDirChange(e: Event) {
  engine.saveConfig({ output_dir: (e.target as HTMLInputElement).value });
}

const tagDisplay = computed(() =>
  engine.params.tag_sync ? engine.params.query || "(同步搜索关键词)" : engine.params.tag || ""
);
</script>

<template>
  <aside class="card p-5 w-full h-full flex flex-col gap-5 overflow-hidden lg:overflow-y-auto">
    <div class="flex items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold text-fg mb-1">运行配置</h2>
        <p class="text-xs text-fg-subtle">设置后点击右侧「启动助手」</p>
      </div>
      <!-- 折叠手柄：箭头指向左侧（折叠后方向是反向） -->
      <button
        type="button"
        class="shrink-0 w-7 h-7 -mt-1 -mr-1 rounded-lg border border-bg-border bg-bg-raised/60 text-fg-muted hover:text-fg hover:bg-bg-raised transition-colors flex items-center justify-center"
        aria-label="折叠配置面板"
        title="折叠配置面板"
        @click="$emit('collapse')"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
    </div>

    <!-- 关键词搜索路线开关 -->
    <div class="rounded-xl bg-bg-raised/60 border border-bg-border p-3">
      <label class="flex items-center justify-between cursor-pointer">
        <span class="text-sm font-medium text-fg">关键词搜索</span>
        <GlassToggle v-model="engine.params.keyword_search" :disabled="engine.running" />
      </label>
      <p class="text-[11px] text-fg-subtle mt-1.5 leading-relaxed">
        {{
          engine.params.keyword_search
            ? "开启：输入关键词后自动跳转到搜索页辅助分析"
            : "关闭：手动模式，请在浏览器中自行搜索后再运行助手"
        }}
      </p>
    </div>

    <!-- 搜索关键词（关键词路线，必填） -->
    <div v-if="engine.params.keyword_search">
      <label class="field-label">
        搜索岗位 <span class="text-danger">*</span>
      </label>
      <input
        v-model="engine.params.query"
        type="text"
        placeholder="例如 AI、运营、前端"
        class="input"
        :class="{ 'input-error': !engine.params.query.trim() }"
        :disabled="engine.running"
      />
      <p class="text-[11px] text-fg-subtle mt-1">必填，提交后自动跳转到对应搜索结果页</p>
    </div>

    <!-- 城市（仅关键词路线） -->
    <div v-if="engine.params.keyword_search">
      <label class="field-label flex items-center justify-between">
        <span>城市</span>
        <button
          type="button"
          class="text-[11px] text-fg-subtle hover:text-fg transition-colors disabled:opacity-50"
          :disabled="engine.running || engine.citiesRefreshing"
          title="基于已登录的浏览器获取城市列表"
          @click="engine.refreshCities()"
        >
          {{ engine.citiesRefreshing ? "刷新中..." : "↻ 刷新" }}
        </button>
      </label>
      <GlassSelect
        :model-value="engine.params.city_code || ''"
        :options="engine.cities"
        :disabled="engine.running"
        filterable
        placeholder="默认浏览器当前城市"
        @update:model-value="onCityChange"
      />
    </div>

    <!-- 获取数量 -->
    <div>
      <label class="field-label">获取数量</label>
      <input
        v-model.number="engine.params.count"
        type="number"
        min="1"
        max="500"
        class="input"
        :disabled="engine.running"
      />
    </div>

    <!-- 薪资范围（初始筛选，单位 K） -->
    <div>
      <label class="field-label">薪资范围 (K/月，可选)</label>
      <div class="flex items-center gap-2">
        <input
          v-model.number="engine.params.salary_min"
          type="number"
          min="0"
          placeholder="最低"
          class="input"
          :disabled="engine.running"
        />
        <span class="text-fg-subtle">~</span>
        <input
          v-model.number="engine.params.salary_max"
          type="number"
          min="0"
          placeholder="最高"
          class="input"
          :disabled="engine.running"
        />
      </div>
      <p class="text-[11px] text-fg-subtle mt-1">自动过滤；结果表可进一步筛选</p>
    </div>

    <!-- 浏览器 -->
    <div>
      <label class="field-label">浏览器</label>
      <GlassSelect
        :model-value="engine.params.browser_type"
        :options="browserOptions"
        :disabled="engine.running"
        @update:model-value="onBrowserChange"
      />
      <div class="flex items-center gap-1.5 mt-1">
        <input
          :value="engine.config?.browser_path || ''"
          type="text"
          placeholder="未检测到浏览器路径"
          class="input !py-1 !text-[11px]"
          :disabled="engine.running"
          @change="onBrowserPathChange"
        />
        <button
          v-if="hasNativePicker"
          type="button"
          class="btn-ghost !py-1 !px-2 text-[11px] shrink-0"
          :disabled="engine.running"
          @click="pickBrowser"
        >
          浏览
        </button>
      </div>
    </div>

    <!-- 输出文件标记 + 同步开关 -->
    <div>
      <label class="field-label flex items-center justify-between">
        <span>输出文件标记 (可选)</span>
        <span class="flex items-center gap-1.5 text-[11px] text-fg-muted font-normal">
          同步关键词
          <GlassCheckbox v-model="engine.params.tag_sync" :disabled="engine.running" />
        </span>
      </label>
      <input
        v-if="!engine.params.tag_sync"
        v-model="engine.params.tag"
        type="text"
        placeholder="例如 stress_test"
        class="input"
        :disabled="engine.running"
      />
      <input
        v-else
        :value="tagDisplay"
        type="text"
        class="input opacity-60"
        disabled
      />
    </div>

    <div class="flex flex-col gap-3.5 pt-1">
      <label class="flex items-center justify-between cursor-pointer">
        <span class="text-sm text-fg-muted">安全模式</span>
        <GlassCheckbox
          v-model="engine.params.safe_mode"
          :disabled="engine.running || engine.params.fast"
        />
      </label>
      <label class="flex items-center justify-between cursor-pointer">
        <span class="text-sm text-fg-muted">
          快速模式
          <span class="text-[11px] text-primary/70">(无人工延迟)</span>
        </span>
        <GlassCheckbox v-model="engine.params.fast" :disabled="engine.running" />
      </label>
      <label class="flex items-center justify-between cursor-pointer">
        <span class="text-sm text-fg-muted">强制启动新浏览器</span>
        <GlassCheckbox v-model="engine.params.new_chrome" :disabled="engine.running" />
      </label>
    </div>

    <!-- 输出目录 -->
    <div class="mt-auto pt-3 border-t border-bg-border">
      <label class="field-label">输出目录</label>
      <div class="flex items-center gap-1.5">
        <input
          :value="engine.config?.output_dir || ''"
          type="text"
          placeholder="-"
          class="input !py-1 !text-[11px]"
          :disabled="engine.running"
          @change="onOutputDirChange"
        />
        <button
          v-if="hasNativePicker"
          type="button"
          class="btn-ghost !py-1 !px-2 text-[11px] shrink-0"
          :disabled="engine.running"
          @click="pickFolder"
        >
          浏览
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.text-danger {
  color: var(--danger);
}
.input-error {
  border-color: var(--danger) !important;
}
</style>
