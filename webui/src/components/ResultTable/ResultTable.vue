<script setup lang="ts">
/**
 * ResultTable：组合 FilterBar + JobTable + JobDetailDrawer
 * 所有筛选状态/派生集中在 useJobFilters()；本组件只负责装配与选中态。
 */
import { ref } from "vue";
import { useJobFilters } from "@/composables/useJobFilters";
import FilterBar from "./FilterBar.vue";
import JobTable from "./JobTable.vue";
import JobDetailDrawer from "./JobDetailDrawer.vue";
import type { Job } from "@/api";

const f = useJobFilters();
const selected = ref<Job | null>(null);
</script>

<template>
  <div class="result-table-root flex flex-col h-full overflow-hidden">
    <FilterBar
      :keyword="f.keyword.value"
      @update:keyword="(v) => (f.keyword.value = v)"
      :salary-min="f.salaryMin.value"
      @update:salary-min="(v) => (f.salaryMin.value = v)"
      :salary-max="f.salaryMax.value"
      @update:salary-max="(v) => (f.salaryMax.value = v)"
      :city-filter="f.cityFilter.value"
      @update:city-filter="(v) => (f.cityFilter.value = v)"
      :experience-filter="f.experienceFilter.value"
      @update:experience-filter="(v) => (f.experienceFilter.value = v)"
      :degree-filter="f.degreeFilter.value"
      @update:degree-filter="(v) => (f.degreeFilter.value = v)"
      :skill-filter="f.skillFilter.value"
      @update:skill-filter="(v) => (f.skillFilter.value = v)"
      :welfare-filter="f.welfareFilter.value"
      @update:welfare-filter="(v) => (f.welfareFilter.value = v)"
      :tag-filter="f.tagFilter.value"
      @update:tag-filter="(v) => (f.tagFilter.value = v)"
      :company-label-filter="f.companyLabelFilter.value"
      @update:company-label-filter="(v) => (f.companyLabelFilter.value = v)"
      :city-options="f.cityOptions.value"
      :experience-options="f.experienceOptions.value"
      :degree-options="f.degreeOptions.value"
      :skill-options="f.skillOptions.value"
      :welfare-options="f.welfareOptions.value"
      :tag-options="f.tagOptions.value"
      :company-label-options="f.companyLabelOptions.value"
      :filtered-count="f.filteredCount.value"
      :total-count="f.totalCount.value"
      :has-active-filter="f.hasActiveFilter.value"
      @clear="f.clearFilters"
    />
    <JobTable :jobs="f.filtered.value" @select="(j) => (selected = j)" />
    <JobDetailDrawer :job="selected" @close="selected = null" />
  </div>
</template>