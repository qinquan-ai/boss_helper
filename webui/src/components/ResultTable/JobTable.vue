<script setup lang="ts">
/**
 * JobTable：表格视图（基于列定义 + 拖拽列宽 + 排序 + 列设置 + CSV 导出）
 * 接收 jobs 与 select 事件；内部维护列显隐 / 列宽 / 排序状态并持久化到 localStorage。
 */
import { computed, ref, watch } from "vue";
import { useEngine } from "@/stores/engine";
import { GlassTag } from "@/ui";
import { trace } from "@/utils/debugTracer";
import type { Job } from "@/api";

// ============================================================================
// 列定义
// ============================================================================
type CellRender = (j: Job) => string | string[];
interface ColumnDef {
  key: keyof Job | "skills" | "welfare" | "tags";
  title: string;
  defaultWidth: number;
  minWidth?: number;
  align?: "left" | "center" | "right";
  defaultVisible?: boolean;
  render?: CellRender;
  sortKey?: (j: Job) => string | number | null;
}

const COLUMNS: ColumnDef[] = [
  { key: "title",       title: "职位",    defaultWidth: 240, minWidth: 120, defaultVisible: true, sortKey: (j) => j.title ?? "" },
  { key: "company",     title: "公司",    defaultWidth: 180, minWidth: 100, defaultVisible: true, sortKey: (j) => j.company ?? "" },
  { key: "salary",      title: "薪资",    defaultWidth: 120, minWidth: 80,  defaultVisible: true, sortKey: (j) => parseSalary(j.salary)?.[0] ?? null },
  { key: "location",    title: "城市",    defaultWidth: 100, minWidth: 70,  defaultVisible: true, sortKey: (j) => j.location ?? "" },
  { key: "experience",  title: "经验",    defaultWidth: 80,  minWidth: 60,  defaultVisible: true, sortKey: (j) => j.experience ?? "" },
  { key: "degree",      title: "学历",    defaultWidth: 80,  minWidth: 60,  defaultVisible: true, sortKey: (j) => j.degree ?? "" },
  { key: "industry",    title: "行业",    defaultWidth: 120, minWidth: 80,  defaultVisible: false, sortKey: (j) => j.industry ?? "" },
  { key: "boss_name",   title: "招聘者",  defaultWidth: 120, minWidth: 80,  defaultVisible: true, sortKey: (j) => j.boss_name ?? "" },
  { key: "skills",      title: "技能",    defaultWidth: 200, minWidth: 120, defaultVisible: false, render: (j) => j.skills ?? [] },
  { key: "welfare",     title: "福利",    defaultWidth: 200, minWidth: 120, defaultVisible: false, render: (j) => j.welfare ?? [] },
  { key: "tags",        title: "标签",    defaultWidth: 160, minWidth: 100, defaultVisible: false, render: (j) => j.job_labels ?? [] },
];

// ============================================================================
// 解析薪资 → [min,max]（单位 K）。无法解析返回 null。
// ============================================================================
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

// ============================================================================
// props / store
// ============================================================================
const props = defineProps<{ jobs: Job[] }>();
const emit = defineEmits<{ (e: "select", j: Job): void }>();
const engine = useEngine();

// 追踪 props.jobs 长度变化
watch(
  () => props.jobs,
  (newJobs) => {
    trace.api("JobTable:jobs", `props.jobs 更新: ${newJobs.length} 条`, { count: newJobs.length });
  }
);

// 追踪 sortedJobs computed 重算
let prevSortedLen = 0;
const sortedJobs = computed(() => {
  const result = !sortKey.value || !sortDir.value
    ? props.jobs
    : (() => {
        const col = COLUMNS.find((c) => c.key === sortKey.value);
        if (!col?.sortKey) return props.jobs;
        const key = col.sortKey;
        const dir = sortDir.value === "asc" ? 1 : -1;
        return [...props.jobs].sort((a, b) => {
          const va = key(a);
          const vb = key(b);
          if (va == null && vb == null) return 0;
          if (va == null) return 1;
          if (vb == null) return -1;
          if (va < vb) return -1 * dir;
          if (va > vb) return 1 * dir;
          return 0;
        });
      })();
  if (result.length !== prevSortedLen) {
    trace.api("JobTable:sortedJobs", `sortedJobs 重算: ${result.length} 条 (props.jobs=${props.jobs.length})`, {
      count: result.length, propsCount: props.jobs.length,
    });
    prevSortedLen = result.length;
  }
  return result;
});

// ============================================================================
// 列显隐 + 列宽（响应式 + localStorage 持久化）
// ============================================================================
const STORAGE_KEY = "resultTable:v1";
interface Persisted {
  visible: Record<string, boolean>;
  widths: Record<string, number>;
}
function loadPersisted(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { visible: {}, widths: {} };
    const p = JSON.parse(raw);
    return { visible: p?.visible ?? {}, widths: p?.widths ?? {} };
  } catch {
    return { visible: {}, widths: {} };
  }
}
const persisted = loadPersisted();

const visibleCols = ref<Record<string, boolean>>(
  Object.fromEntries(
    COLUMNS.map((c) => [c.key, persisted.visible[c.key] ?? c.defaultVisible ?? true])
  )
);
const colWidths = ref<Record<string, number>>(
  Object.fromEntries(COLUMNS.map((c) => [c.key, persisted.widths[c.key] ?? c.defaultWidth]))
);

watch(
  [visibleCols, colWidths],
  () => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ visible: visibleCols.value, widths: colWidths.value })
      );
    } catch { /* 容量错误忽略 */ }
  },
  { deep: true }
);

const visibleColumnList = computed(() => COLUMNS.filter((c) => visibleCols.value[c.key]));

// ============================================================================
// 列宽拖拽（指令式自写，避免引入重型库）
// ============================================================================
let dragCol: string | null = null;
let dragStartX = 0;
let dragStartW = 0;
let dragMinW = 60;
let dragOriginalW = 0;
let rafId: number | null = null;

function onResizeStart(e: PointerEvent, colKey: string) {
  e.preventDefault();
  e.stopPropagation();

  dragCol = colKey;
  dragStartX = e.clientX;
  dragStartW = colWidths.value[colKey] ?? 100;
  dragMinW = COLUMNS.find((c) => c.key === colKey)?.minWidth ?? 60;
  dragOriginalW = dragStartW;

  // pointer capture：鼠标甩出窗口 onPointerUp 仍能触发
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);

  // 拖动时禁用文字选中、列高亮、document 光标
  document.body.style.userSelect = "none";
  document.body.style.cursor = "col-resize";
  const tableWrap = document.querySelector<HTMLElement>(".table-resize-wrap");
  if (tableWrap) tableWrap.classList.add("is-dragging");

  // 一次性找所有受影响的 td（避免每帧 querySelector）
  const affectedEls: HTMLElement[] = Array.from(
    document.querySelectorAll(`th[data-col="${colKey}"], td[data-col="${colKey}"]`)
  );
  const th = affectedEls[0];

  const onMove = (ev: PointerEvent) => {
    if (dragCol !== colKey) return;
    if (rafId !== null) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      rafId = null;
      const w = Math.max(dragMinW, dragStartW + (ev.clientX - dragStartX));
      const rounded = Math.round(w);
      colWidths.value[colKey] = rounded;
      // 拖动中实时更新 td/th 宽度（colgroup 的 :style 会自动响应）
      affectedEls.forEach((el) => (el.style.width = rounded + "px"));
      if (th) th.style.width = rounded + "px";
    });
  };

  const onUp = (ev: PointerEvent) => {
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
    dragCol = null;
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
    const tableWrap = document.querySelector<HTMLElement>(".table-resize-wrap");
    if (tableWrap) tableWrap.classList.remove("is-dragging");
    // 清除 inline style，让 Vue 响应式接管
    const affected: HTMLElement[] = Array.from(
      document.querySelectorAll(`th[data-col="${colKey}"], td[data-col="${colKey}"]`)
    );
    affected.forEach((el) => (el.style.width = ""));
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
  };

  const onKeydown = (ev: KeyboardEvent) => {
    if (ev.key === "Escape" && dragCol === colKey) {
      if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
      dragCol = null;
      colWidths.value[colKey] = dragOriginalW;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      const tableWrap = document.querySelector<HTMLElement>(".table-resize-wrap");
      if (tableWrap) tableWrap.classList.remove("is-dragging");
      const affected: HTMLElement[] = Array.from(
        document.querySelectorAll(`th[data-col="${colKey}"], td[data-col="${colKey}"]`)
      );
      affected.forEach((el) => (el.style.width = ""));
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.removeEventListener("keydown", onKeydown);
    }
  };

  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
  document.addEventListener("keydown", onKeydown);
}

// ============================================================================
// 排序
// ============================================================================
type SortDir = "asc" | "desc" | null;
const sortKey = ref<string | null>(null);
const sortDir = ref<SortDir>(null);

function clickHeader(col: ColumnDef) {
  if (!col.sortKey) return;
  if (sortKey.value !== col.key) {
    sortKey.value = col.key as string;
    sortDir.value = "asc";
  } else if (sortDir.value === "asc") {
    sortDir.value = "desc";
  } else {
    sortKey.value = null;
    sortDir.value = null;
  }
}

// ============================================================================
// CSV 导出
// ============================================================================
function exportCsv() {
  const cols = visibleColumnList.value;
  const header = cols.map((c) => `"${c.title}"`).join(",");
  const rows = sortedJobs.value.map((j) =>
    cols.map((c) => {
      const v = c.render ? c.render(j) : (j as any)[c.key];
      const text = Array.isArray(v) ? v.join(" / ") : (v ?? "");
      return `"${String(text).replace(/"/g, '""')}"`;
    }).join(",")
  );
  const csv = "\uFEFF" + [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = (engine.currentFile || "jobs").replace(/\.json$/, "") + ".csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

// ============================================================================
// 列设置面板
// ============================================================================
const showColPanel = ref(false);
</script>

<template>
  <div class="flex flex-col flex-1 min-h-0 overflow-hidden">
    <!-- 工具栏：列设置 + 刷新 + CSV -->
    <div class="flex items-center gap-2 px-4 py-2 border-b border-bg-border">
      <button
        class="btn-ghost !py-1.5 text-xs"
        :class="{ 'is-on': showColPanel }"
        @click="showColPanel = !showColPanel"
      >列设置</button>
      <span class="text-[11px] text-fg-subtle">{{ sortedJobs.length }} 行</span>
      <div class="flex-1"></div>
      <button class="btn-primary !py-1.5 text-xs" @click="exportCsv">导出 CSV</button>
    </div>

    <!-- 列设置面板 -->
    <transition name="slide-down">
      <div
        v-if="showColPanel"
        class="px-4 py-3 border-b border-bg-border bg-bg-raised/40 grid gap-1.5"
        style="grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));"
      >
        <label
          v-for="c in COLUMNS"
          :key="'vis-' + c.key"
          class="flex items-center gap-2 text-xs text-fg-muted cursor-pointer select-none"
        >
          <input
            type="checkbox"
            :checked="visibleCols[c.key]"
            class="gcheck-native"
            @change="visibleCols[c.key] = ($event.target as HTMLInputElement).checked"
          />
          <span>{{ c.title }}</span>
          <span class="text-[10px] text-fg-subtle ml-auto">{{ colWidths[c.key] }}px</span>
        </label>
      </div>
    </transition>

    <!-- 表格 -->
    <div class="table-resize-wrap flex-1 overflow-auto">
      <table class="w-full text-sm border-collapse" style="table-layout: fixed;">
        <colgroup>
          <col
            v-for="c in visibleColumnList"
            :key="'cg-' + c.key"
            :style="{ width: colWidths[c.key] + 'px' }"
          />
        </colgroup>
        <thead class="sticky top-0 bg-bg-panel z-10">
          <tr class="text-left text-xs text-fg-subtle border-b border-bg-border">
            <th
              v-for="(c, ci) in visibleColumnList"
              :key="'th-' + c.key"
              :data-col="c.key"
              class="relative px-3 py-2.5 font-medium select-none border-l border-bg-border first:border-l-0"
              :class="[
                c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left',
                c.sortKey ? 'cursor-pointer hover:text-fg' : ''
              ]"
              @click="clickHeader(c)"
            >
              <span class="inline-flex items-center gap-1">
                <span>{{ c.title }}</span>
                <span v-if="sortKey === c.key" class="text-fg">
                  {{ sortDir === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
              <span
                class="col-resizable"
                @pointerdown="(e) => onResizeStart(e, c.key as string)"
                @click.stop
                :title="`拖动调整「${c.title}」宽度`"
              ></span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(j, i) in sortedJobs"
            :key="(j.collected_at || '') + '-' + i"
            class="row-job border-b border-bg-border hover:bg-bg-raised cursor-pointer transition-colors"
            @click="emit('select', j)"
          >
            <td
              v-for="c in visibleColumnList"
              :key="'td-' + c.key + '-' + i"
              :data-col="c.key"
              class="px-3 py-2.5 border-l border-bg-border first:border-l-0"
              :class="c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : ''"
            >
              <template v-if="!c.render">
                <span class="text-fg font-medium truncate-cell">{{ (j as any)[c.key] || '-' }}</span>
              </template>
              <template v-else-if="c.key === 'skills' || c.key === 'welfare' || c.key === 'tags'">
                <span
                  v-if="!(c.render(j) as string[]).length"
                  class="text-fg-subtle"
                >-</span>
                <span v-else class="flex flex-wrap gap-1">
                  <GlassTag
                    v-for="t in (c.render(j) as string[])"
                    :key="t"
                    :variant="
                      c.key === 'skills' ? 'brand' :
                      c.key === 'welfare' ? 'success' : 'default'
                    "
                  >{{ t }}</GlassTag>
                </span>
              </template>
              <template v-else-if="c.key === 'salary'">
                <span class="text-fg whitespace-nowrap font-medium">{{ j.salary || '-' }}</span>
              </template>
              <template v-else>
                <span class="text-fg-muted truncate-cell">{{ c.render(j) }}</span>
              </template>
            </td>
          </tr>
          <tr v-if="!sortedJobs.length">
            <td
              :colspan="visibleColumnList.length"
              class="px-4 py-10 text-center text-fg-subtle"
            >暂无数据。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: max-height 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  max-height: 0;
  opacity: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 200px;
  opacity: 1;
}

/* 常驻分隔线 + 拖拽热区 */
.col-resizable {
  position: absolute;
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
  touch-action: none;
  /* 默认：细竖线 */
  background: rgba(255, 255, 255, 0.1);
  transition: background 0.12s ease, width 0.12s ease;
}
.col-resizable:hover {
  /* hover：稍亮 */
  background: rgba(255, 255, 255, 0.35);
  width: 4px;
  right: -1px;
}

.table-resize-wrap.is-dragging,
.table-resize-wrap.is-dragging * {
  cursor: col-resize !important;
  user-select: none !important;
}
.table-resize-wrap.is-dragging .col-resizable {
  background: rgba(255, 255, 255, 0.6);
  width: 3px;
  right: -1px;
}

.truncate-cell {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.row-job {
  transition: background-color 0.12s ease;
}

.gcheck-native {
  appearance: none;
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg);
  cursor: pointer;
  flex-shrink: 0;
  position: relative;
  margin: 0;
}
.gcheck-native:checked {
  background: var(--accent);
  border-color: transparent;
}
.gcheck-native:checked::after {
  content: "";
  position: absolute;
  left: 3px; top: 0px;
  width: 4px; height: 8px;
  border-right: 2px solid var(--accent-fg);
  border-bottom: 2px solid var(--accent-fg);
  transform: rotate(45deg);
}

.btn-ghost.is-on {
  background: var(--accent);
  color: var(--accent-fg);
}
</style>