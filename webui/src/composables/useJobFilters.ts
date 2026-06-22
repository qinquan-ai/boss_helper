import { computed, ref } from "vue";
import { useEngine } from "@/stores/engine";

/**
 * 所有筛选状态与派生，集中在此处供父组件 + FilterBar 共享。
 * - 状态：keyword / salaryMin / salaryMax / 7 个集合筛选 ref
 * - 派生：每个集合的去重 option（取自 engine.jobs）
 * - 派生：filtered（经过 keyword + 薪资 + 7 个 chip 过滤后的列表）
 */
const COLLECTION_KEYS = [
  "skills",
  "welfare",
  "job_labels",
  "company_labels",
  "city",
  "experience",
  "degree",
] as const;

type CollectionKey = (typeof COLLECTION_KEYS)[number];

/** 从 jobs 中收集某字段的去重 option，单值字段走 fallback，单数组字段直接 flatMap。 */
function collectOptions(
  jobs: any[],
  key: CollectionKey,
  fallbackKey?: string
): string[] {
  const vals: string[] = [];
  for (const j of jobs) {
    const arr = j[key];
    if (Array.isArray(arr)) {
      for (const v of arr) if (typeof v === "string" && v) vals.push(v);
    } else if (fallbackKey && typeof j[fallbackKey] === "string" && j[fallbackKey]) {
      vals.push(j[fallbackKey]);
    }
  }
  return Array.from(new Set(vals)).sort().slice(0, 80);
}

/** 多值命中：未选 = 放行；已选 = 元素集合与选中集合有交集即放行。 */
function multiMatch(selected: string[], itemValues: string[] | undefined): boolean {
  if (!selected.length) return true;
  if (!itemValues || !itemValues.length) return false;
  return selected.some((s) => itemValues.includes(s));
}

/** 单值命中：未选 = 放行；已选 = 该值在选中集合中即放行。 */
function singleMatch(selected: string[], itemValue: string | undefined): boolean {
  if (!selected.length) return true;
  if (!itemValue) return false;
  return selected.includes(itemValue);
}

export function useJobFilters() {
  const engine = useEngine();

  const keyword = ref("");
  const salaryMin = ref<number | null>(null);
  const salaryMax = ref<number | null>(null);

  const cityFilter = ref<string[]>([]);
  const experienceFilter = ref<string[]>([]);
  const degreeFilter = ref<string[]>([]);
  const skillFilter = ref<string[]>([]);
  const welfareFilter = ref<string[]>([]);
  const tagFilter = ref<string[]>([]);
  const companyLabelFilter = ref<string[]>([]);

  /** 每个 option 都是基于 engine.jobs 派生的 computed。 */
  function makeOptions(key: CollectionKey, fallbackKey?: string) {
    return computed(() => collectOptions(engine.jobs as any[], key, fallbackKey));
  }
  const cityOptions = makeOptions("city", "location");
  const experienceOptions = makeOptions("experience", "experience");
  const degreeOptions = makeOptions("degree", "degree");
  const skillOptions = makeOptions("skills");
  const welfareOptions = makeOptions("welfare");
  const tagOptions = makeOptions("job_labels");
  const companyLabelOptions = makeOptions("company_labels");

  /** 经过所有筛选条件后的 job 列表。 */
  const filtered = computed(() => {
    const k = keyword.value.trim().toLowerCase();
    const min = salaryMin.value;
    const max = salaryMax.value;
    return (engine.jobs as any[]).filter((j) => {
      if (!singleMatch(cityFilter.value, j.location)) return false;
      if (!singleMatch(experienceFilter.value, j.experience)) return false;
      if (!singleMatch(degreeFilter.value, j.degree)) return false;
      if (!multiMatch(skillFilter.value, j.skills)) return false;
      if (!multiMatch(welfareFilter.value, j.welfare)) return false;
      if (!multiMatch(tagFilter.value, j.job_labels)) return false;
      if (!multiMatch(companyLabelFilter.value, j.company_labels)) return false;

      if (min != null && j.salaryMin != null && j.salaryMin < min) return false;
      if (max != null && j.salaryMax != null && j.salaryMax > max) return false;

      if (k) {
        const hay = [
          j.title,
          j.company,
          j.salary,
          j.location,
          j.experience,
          j.degree,
          j.industry,
          j.jd,
          ...((j.skills as string[]) ?? []),
          ...((j.welfare as string[]) ?? []),
          ...((j.job_labels as string[]) ?? []),
          ...((j.company_labels as string[]) ?? []),
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(k)) return false;
      }
      return true;
    });
  });

  const filteredCount = computed(() => filtered.value.length);
  const totalCount = computed(() => engine.jobs.length);

  const hasActiveFilter = computed(
    () =>
      !!keyword.value.trim() ||
      salaryMin.value != null ||
      salaryMax.value != null ||
      cityFilter.value.length > 0 ||
      experienceFilter.value.length > 0 ||
      degreeFilter.value.length > 0 ||
      skillFilter.value.length > 0 ||
      welfareFilter.value.length > 0 ||
      tagFilter.value.length > 0 ||
      companyLabelFilter.value.length > 0
  );

  function clearFilters() {
    keyword.value = "";
    salaryMin.value = null;
    salaryMax.value = null;
    cityFilter.value = [];
    experienceFilter.value = [];
    degreeFilter.value = [];
    skillFilter.value = [];
    welfareFilter.value = [];
    tagFilter.value = [];
    companyLabelFilter.value = [];
  }

  return {
    // 状态
    keyword,
    salaryMin,
    salaryMax,
    cityFilter,
    experienceFilter,
    degreeFilter,
    skillFilter,
    welfareFilter,
    tagFilter,
    companyLabelFilter,
    // 派生 option
    cityOptions,
    experienceOptions,
    degreeOptions,
    skillOptions,
    welfareOptions,
    tagOptions,
    companyLabelOptions,
    // 派生列表与计数
    filtered,
    filteredCount,
    totalCount,
    hasActiveFilter,
    // 动作
    clearFilters,
  };
}