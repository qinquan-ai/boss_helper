<script setup lang="ts">
/**
 * FilterBar：顶部筛选栏（搜索 + 薪资范围 + 7 个集合 chip 多选）
 * 所有状态由父组件传入 + 通过 update:* 事件回传（保持单向数据流）。
 */
import { computed, ref } from "vue";
import { useEngine } from "@/stores/engine";
import { GlassSelect } from "@/ui";
import ChipGroup from "./ChipGroup.vue";

const props = defineProps<{
  keyword: string;
  salaryMin: number | null;
  salaryMax: number | null;
  cityFilter: string[];
  experienceFilter: string[];
  degreeFilter: string[];
  skillFilter: string[];
  welfareFilter: string[];
  tagFilter: string[];
  companyLabelFilter: string[];
  cityOptions: string[];
  experienceOptions: string[];
  degreeOptions: string[];
  skillOptions: string[];
  welfareOptions: string[];
  tagOptions: string[];
  companyLabelOptions: string[];
  filteredCount: number;
  totalCount: number;
  hasActiveFilter: boolean;
}>();

const emit = defineEmits<{
  (e: "update:keyword", v: string): void;
  (e: "update:salaryMin", v: number | null): void;
  (e: "update:salaryMax", v: number | null): void;
  (e: "update:cityFilter", v: string[]): void;
  (e: "update:experienceFilter", v: string[]): void;
  (e: "update:degreeFilter", v: string[]): void;
  (e: "update:skillFilter", v: string[]): void;
  (e: "update:welfareFilter", v: string[]): void;
  (e: "update:tagFilter", v: string[]): void;
  (e: "update:companyLabelFilter", v: string[]): void;
  (e: "clear"): void;
}>();

const engine = useEngine();

const fileOptions = computed(() =>
  engine.resultFiles.map((f) => ({ label: f, value: f }))
);
function onFileChange(v: string) {
  engine.loadResults(v.replace("jobs_", "").replace(".json", ""));
}
function refresh() {
  engine.loadResults();
}

// chips 行折叠状态（仅控制下方 chips 行的展开/收起，不影响上方工具栏）
const chipsExpanded = ref(true);
</script>

<template>
  <!-- ============================== 顶部工具栏 ============================== -->
  <div class="flex flex-wrap items-center gap-3 px-4 py-2.5 border-b border-bg-border">
    <span class="text-sm font-semibold text-fg">岗位列表</span>
    <span class="text-[11px] text-fg-subtle">
      {{ props.filteredCount }} / {{ props.totalCount }} 条
    </span>

    <div v-if="engine.resultFiles.length" class="w-52">
      <GlassSelect
        :model-value="engine.currentFile || ''"
        :options="fileOptions"
        @update:model-value="onFileChange"
      />
    </div>

    <div class="flex-1"></div>

    <!-- 薪资范围 -->
    <div class="flex items-center gap-1 text-xs text-fg-subtle">
      <span>薪资</span>
      <input
        type="number" min="0" placeholder="最低"
        :value="props.salaryMin ?? ''"
        @input="emit('update:salaryMin', ($event.target as HTMLInputElement).value === '' ? null : Number(($event.target as HTMLInputElement).value))"
        class="input !w-16 !py-1.5 text-xs"
      />
      <span>~</span>
      <input
        type="number" min="0" placeholder="最高"
        :value="props.salaryMax ?? ''"
        @input="emit('update:salaryMax', ($event.target as HTMLInputElement).value === '' ? null : Number(($event.target as HTMLInputElement).value))"
        class="input !w-16 !py-1.5 text-xs"
      />
      <span>K</span>
    </div>

    <input
      :value="props.keyword"
      @input="emit('update:keyword', ($event.target as HTMLInputElement).value)"
      placeholder="搜索职位/公司/技能/福利..."
      class="input !w-56 !py-1.5 text-xs"
    />

    <button
      v-if="props.hasActiveFilter"
      class="btn-ghost !py-1.5 text-xs"
      @click="emit('clear')"
    >清空筛选</button>

    <button class="btn-ghost !py-1.5 text-xs" @click="refresh">刷新</button>
  </div>

  <!-- ============================== 集合筛选条（chips，可折叠） ============================== -->
  <button
    class="flex items-center gap-2 px-4 py-1.5 border-b border-bg-border w-full text-left text-[11px] text-fg-subtle hover:bg-bg-raised/40 transition-colors"
    @click="chipsExpanded = !chipsExpanded"
    :title="chipsExpanded ? '收起筛选条件' : '展开筛选条件'"
  >
    <span>筛选条件</span>
    <span v-if="props.hasActiveFilter" class="text-accent">· 已启用</span>
    <div class="flex-1"></div>
    <span class="transition-transform" :class="chipsExpanded ? 'rotate-180' : ''">▾</span>
  </button>
  <transition name="chip-collapse">
    <div
      v-if="chipsExpanded"
      class="px-4 py-2 border-b border-bg-border flex flex-wrap gap-x-4 gap-y-1.5"
    >
      <ChipGroup label="城市" :model-value="props.cityFilter" :options="props.cityOptions"
        @update:model-value="emit('update:cityFilter', $event)" />
      <ChipGroup label="经验" :model-value="props.experienceFilter" :options="props.experienceOptions"
        @update:model-value="emit('update:experienceFilter', $event)" />
      <ChipGroup label="学历" :model-value="props.degreeFilter" :options="props.degreeOptions"
        @update:model-value="emit('update:degreeFilter', $event)" />
      <ChipGroup label="技能" :model-value="props.skillFilter" :options="props.skillOptions"
        @update:model-value="emit('update:skillFilter', $event)" />
      <ChipGroup label="福利" :model-value="props.welfareFilter" :options="props.welfareOptions"
        @update:model-value="emit('update:welfareFilter', $event)" />
      <ChipGroup label="岗位标签" :model-value="props.tagFilter" :options="props.tagOptions"
        @update:model-value="emit('update:tagFilter', $event)" />
      <ChipGroup label="公司标签" :model-value="props.companyLabelFilter" :options="props.companyLabelOptions"
        @update:model-value="emit('update:companyLabelFilter', $event)" />
    </div>
  </transition>
</template>

<style scoped>
.chip-collapse-enter-active,
.chip-collapse-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease, max-height 0.2s ease;
  overflow: hidden;
}
.chip-collapse-enter-from,
.chip-collapse-leave-to {
  opacity: 0;
  transform: translateY(-2px);
  max-height: 0;
}
.chip-collapse-enter-to,
.chip-collapse-leave-from {
  opacity: 1;
  transform: translateY(0);
  max-height: 400px;
}
</style>