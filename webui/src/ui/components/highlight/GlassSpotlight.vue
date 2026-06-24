<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    targetEl?: HTMLElement | null;
    bubblePosition?: Record<string, string | number>;
    highlightStyle?: Record<string, string | number>;
    theme?: {
      borderColor?: string;
      glowColor?: string;
      innerGlowColor?: string;
      pulseColor?: string;
    };
    padding?: number;
    transitionDuration?: number;
    showPulse?: boolean;
  }>(),
  {
    padding: 8,
    transitionDuration: 300,
    showPulse: true,
  }
);

const emit = defineEmits<{
  "update:modelValue": [val: boolean];
}>();

// ── 主题默认值 ──────────────────────────────────────────────
const brandRgb = "59 130 246";
// 紫粉 + 青色渐变主题
const purpleCyanRgb = "186 66 255";
const cyanRgb = "0 225 255";

const resolved = computed(
  () => ({
    borderColor: props.theme?.borderColor ?? `rgb(${purpleCyanRgb})`,
    glowColor: props.theme?.glowColor ?? `rgba(${purpleCyanRgb}, 0.5)`,
    innerGlowColor: props.theme?.innerGlowColor ?? `rgba(${purpleCyanRgb}, 0.15)`,
    pulseColor: props.theme?.pulseColor ?? `rgba(${cyanRgb}, 0.7)`,
  })
);

// ── 高亮框坐标计算 ─────────────────────────────────────────
const highlightStyle = ref<Record<string, string | number>>({});

const updateHighlight = () => {
  if (!props.modelValue || !props.targetEl) {
    highlightStyle.value = {};
    return;
  }
  const rect = props.targetEl.getBoundingClientRect();
  const p = props.padding ?? 8;
  highlightStyle.value = {
    top: rect.top - p,
    left: rect.left - p,
    width: rect.width + p * 2,
    height: rect.height + p * 2,
  };
};

const mergedHighlightStyle = computed(
  () => ({
    ...highlightStyle.value,
    ...(props.highlightStyle ?? {}),
  })
);

// ── 监听 & 生命周期 ─────────────────────────────────────────
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      nextTick(() => {
        requestAnimationFrame(() => updateHighlight());
      });
    }
  }
);

watch(
  () => props.targetEl,
  () => {
    if (props.modelValue) {
      nextTick(() => {
        requestAnimationFrame(() => updateHighlight());
      });
    }
  }
);

const resizeObserver = ref<ResizeObserver | null>(null);

const stopObserve = () => {
  if (resizeObserver.value) {
    resizeObserver.value.disconnect();
    resizeObserver.value = null;
  }
};

const startObserve = () => {
  stopObserve();
  if (!props.targetEl) return;
  resizeObserver.value = new ResizeObserver(() => {
    requestAnimationFrame(() => updateHighlight());
  });
  resizeObserver.value.observe(props.targetEl);
};

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      nextTick(() => startObserve());
    } else {
      stopObserve();
    }
  }
);

watch(
  () => props.targetEl,
  (el) => {
    if (props.modelValue) {
      nextTick(() => {
        if (el) startObserve();
        else stopObserve();
      });
    }
  }
);

const onGlobalUpdate = () => {
  if (props.modelValue) {
    requestAnimationFrame(() => updateHighlight());
  }
};

import { onMounted, onUnmounted } from "vue";

onMounted(() => {
  window.addEventListener("resize", onGlobalUpdate);
  window.addEventListener("scroll", onGlobalUpdate, true);
});

onUnmounted(() => {
  window.removeEventListener("resize", onGlobalUpdate);
  window.removeEventListener("scroll", onGlobalUpdate, true);
  stopObserve();
});

// ── 关闭 ────────────────────────────────────────────────────
const handleClose = () => emit("update:modelValue", false);

// ── 暴露方法 ────────────────────────────────────────────────
const updatePosition = () => updateHighlight();
defineExpose({ updatePosition });

// ── Slots ───────────────────────────────────────────────────
const slots = defineSlots<{
  default?: () => unknown;
  overlay?: (props: {
    highlightStyle: Record<string, string | number>;
    bubblePosition: Record<string, string | number>;
    resolved: {
      borderColor: string;
      glowColor: string;
      innerGlowColor: string;
      pulseColor: string;
    };
    showPulse: boolean;
    transitionDuration: number;
    handleClose: () => void;
  }) => unknown;
}>();
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-[9995] pointer-events-none">
      <!-- 自定义 overlay 插槽 -->
      <slot
        v-if="$slots.overlay"
        name="overlay"
        :highlight-style="mergedHighlightStyle"
        :bubble-position="bubblePosition ?? {}"
        :resolved="resolved"
        :show-pulse="showPulse"
        :transition-duration="transitionDuration"
        :handle-close="handleClose"
      />

      <!-- 默认渲染：描边 + 光晕高亮框 -->
      <template v-else>
        <div
          class="absolute rounded-xl pointer-events-none highlight-glow-box"
          :style="{
            ...mergedHighlightStyle,
            transition: `all ${transitionDuration}ms ease-out`,
          }"
        >
          <div class="highlight-border-flow"></div>
          <div
            v-if="showPulse"
            class="absolute inset-0 rounded-xl pointer-events-none animate-pulse-ring"
          ></div>
        </div>

        <slot name="default" />
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
.highlight-glow-box {
  box-shadow: 0px -5px 25px 0px rgba(186, 66, 255, 0.5), 0px 5px 25px 0px rgba(0, 225, 255, 0.5);
  background: transparent;
}

.highlight-border-flow {
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  overflow: hidden;
}

.highlight-border-flow::before {
  content: '';
  position: absolute;
  width: 250%;
  height: 250%;
  top: -75%;
  left: -75%;
  background-image: linear-gradient(rgb(186, 66, 255) 35%, rgb(0, 225, 255));
  animation: spinning82341 1.7s linear infinite;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  -webkit-mask-composite: xor;
  padding: 2px;
}

@keyframes spinning82341 {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(0, 225, 255, 0.4);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(0, 225, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 225, 255, 0);
  }
}

.animate-pulse-ring {
  animation: pulse-ring 1.7s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  border: 2px solid rgba(0, 225, 255, 0.7);
}
</style>

