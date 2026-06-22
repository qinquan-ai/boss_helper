<script setup lang="ts">
import { ref } from "vue";
import {
  GlassButton,
  MatteButton,
  GlassCard,
  GlassTag,
  GlassToggle,
  GlassInput,
  GlassSelect,
  GlassCheckbox,
} from "@/ui";

const toggleA = ref(true);
const toggleB = ref(false);
const text = ref("");
const selectVal = ref("chrome");
const checkA = ref(true);
const checkB = ref(false);

const selectOptions = [
  { label: "Chrome", value: "chrome" },
  { label: "Edge", value: "edge" },
  { label: "Firefox", value: "firefox" },
];
</script>

<template>
  <div class="showcase">
    <div class="showcase__intro">
      <h2>组件预览 · 毛玻璃</h2>
      <p>现代毛玻璃设计语言 · 双色调（顶栏可切换 light / dark）</p>
    </div>

    <div class="showcase__grid">
      <GlassCard>
        <template #header>Button · 按钮</template>
        <div class="row">
          <GlassButton variant="solid">Solid</GlassButton>
          <GlassButton variant="glass">Glass</GlassButton>
          <GlassButton variant="ghost">Ghost</GlassButton>
          <GlassButton variant="danger">Danger</GlassButton>
        </div>
        <div class="row">
          <GlassButton size="sm">Small</GlassButton>
          <GlassButton size="md">Medium</GlassButton>
          <GlassButton size="lg">Large</GlassButton>
          <GlassButton :loading="true">Loading</GlassButton>
        </div>
        <div class="row">
          <MatteButton>Matte 金属</MatteButton>
          <MatteButton size="lg">Matte Large</MatteButton>
        </div>
      </GlassCard>

      <GlassCard>
        <template #header>Select &amp; Checkbox · 选择 / 选中框</template>
        <div class="col">
          <GlassSelect v-model="selectVal" :options="selectOptions" />
          <span class="muted">当前：{{ selectVal }}</span>
        </div>
        <div class="row">
          <label class="check-row"><GlassCheckbox v-model="checkA" /> 选项 A</label>
          <label class="check-row"><GlassCheckbox v-model="checkB" /> 选项 B</label>
          <label class="check-row"><GlassCheckbox :disabled="true" /> 禁用</label>
        </div>
      </GlassCard>

      <GlassCard>
        <template #header>Tag · 标签</template>
        <div class="row">
          <GlassTag>默认</GlassTag>
          <GlassTag variant="brand">品牌</GlassTag>
          <GlassTag variant="success">在线</GlassTag>
          <GlassTag variant="danger">警告</GlassTag>
        </div>
      </GlassCard>

      <GlassCard>
        <template #header>Toggle · 开关</template>
        <div class="row">
          <GlassToggle v-model="toggleA" />
          <span class="muted">{{ toggleA ? "开" : "关" }}</span>
          <GlassToggle v-model="toggleB" />
          <span class="muted">{{ toggleB ? "开" : "关" }}</span>
          <GlassToggle :disabled="true" />
          <span class="muted">禁用</span>
        </div>
      </GlassCard>

      <GlassCard>
        <template #header>Input · 输入框</template>
        <div class="col">
          <GlassInput v-model="text" placeholder="搜索职位关键词..." />
          <span class="muted">值：{{ text || "(空)" }}</span>
        </div>
      </GlassCard>
    </div>
  </div>
</template>

<style scoped>
.showcase {
  min-height: 480px;
  max-height: calc(100dvh - var(--header-h, 56px) - 16rem);
  overflow-y: auto;
  padding: 1.5rem;
  background: radial-gradient(
      1200px 600px at 30% -10%,
      var(--glass-bg-hover),
      transparent 60%
    ),
    var(--app-bg);
  border-radius: 16px;
}
.showcase__intro h2 {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--fg);
}
.showcase__intro p {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--fg-subtle);
}
.showcase__grid {
  margin-top: 1.25rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.6rem;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-top: 0.6rem;
}
.check-row {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: var(--fg-muted);
  cursor: pointer;
}
.muted {
  color: var(--fg-subtle);
  font-size: 0.8rem;
}
</style>
