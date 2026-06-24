<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();

const currentStep = ref(0);
const highlightStyle = ref({
  top: "0px",
  left: "0px",
  width: "0px",
  height: "0px",
  opacity: 0,
});
const bubbleStyle = ref({
  top: "0px",
  left: "0px",
  transform: "none",
  opacity: 0,
});

interface TourStep {
  title: string;
  desc: string;
  target: string | null;
  position: "bottom" | "top" | "left" | "right" | "center";
}

const steps: TourStep[] = [
  {
    title: "欢迎使用 BOSS 直聘助手 👋",
    desc: "这是一款轻量、安全、且免去任何代码环境配置的桌面岗位分析整理工具。\n\n只需简单点击几下，即可自动化收集、整理及本地筛选你感兴趣的岗位。让我们用 1 分钟快速熟悉它的使用吧！",
    target: null,
    position: "center",
  },
  {
    title: "⚙️ 运行参数配置",
    desc: "在这里，你可以自定义你需要采集的岗位数量、薪资范围、使用的浏览器路径，以及设置最终保存结果的输出目录（默认输出到桌面）。",
    target: "#config-panel",
    position: "right",
  },
  {
    title: "🔄 自动与手动模式切换",
    desc: "【开启关键词】输入关键词和城市后，助手将全自动跳转检索；\n\n【关闭关键词】进入完全手动路由，你可以自由在浏览器里滚动、点下一页，助手机智地在后台静默提取，同样支持防漏重和「无缝续接」。",
    target: "#keyword-search-card",
    position: "right",
  },
  {
    title: "🚀 一键启动助手",
    desc: "一切配置就绪后，点击此处的「启动助手」按钮。这会拉起一个干净受控的 Chrome/Edge 浏览器窗口。\n\n【首次启动】需要你在这个浏览器内扫码登录一次，之后再运行可完美自动复用登录态！",
    target: "#start-btn",
    position: "bottom",
  },
  {
    title: "📊 运行控制与实时日志",
    desc: "点击这里可以在「实时日志」与「岗位列表」之间自如切换。启动后在这里会打印每一条岗位的整理进度。这里也是你暂停、继续或停止整个数据整理的核心控制中心。",
    target: "#control-bar-main",
    position: "bottom",
  },
  {
    title: "📂 结果查看、筛选与导出",
    desc: "数据整理完毕后，切换到「岗位列表」Tab，你可以看到所有整理好的记录，通过我们优化后的极简「筛选」按钮可以进行多重秒级本地过滤，并一键导出为 Excel/Markdown。",
    target: "#tab-bar",
    position: "bottom",
  },
];

const updatePosition = () => {
  if (!props.modelValue) return;

  const step = steps[currentStep.value];
  if (!step) return;

  if (!step.target) {
    // 居中显示
    highlightStyle.value = {
      top: "0px",
      left: "0px",
      width: "0px",
      height: "0px",
      opacity: 0,
    };
    bubbleStyle.value = {
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      opacity: 1,
    };
    return;
  }

  const el = document.querySelector(step.target);
  if (!el) {
    // 找不到目标，退化为居中显示
    highlightStyle.value = {
      top: "0px",
      left: "0px",
      width: "0px",
      height: "0px",
      opacity: 0,
    };
    bubbleStyle.value = {
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      opacity: 1,
    };
    return;
  }

  // 获取目标元素的位置尺寸
  const rect = el.getBoundingClientRect();
  const offset = 8; // 预留一点高亮的边距

  highlightStyle.value = {
    top: `${rect.top - offset}px`,
    left: `${rect.left - offset}px`,
    width: `${rect.width + offset * 2}px`,
    height: `${rect.height + offset * 2}px`,
    opacity: 1,
  };

  // 计算气泡位置
  const bubbleGap = 16;
  let top = 0;
  let left = 0;
  let transform = "none";

  if (step.position === "right") {
    top = rect.top + rect.height / 2;
    left = rect.right + offset + bubbleGap;
    transform = "translateY(-50%)";
  } else if (step.position === "left") {
    top = rect.top + rect.height / 2;
    left = rect.left - offset - bubbleGap;
    transform = "translate(-100%, -50%)";
  } else if (step.position === "top") {
    top = rect.top - offset - bubbleGap;
    left = rect.left + rect.width / 2;
    transform = "translate(-50%, -100%)";
  } else {
    // default bottom
    top = rect.bottom + offset + bubbleGap;
    left = rect.left + rect.width / 2;
    transform = "translate(-50%, 0)";
  }

  // 防溢出视口边界调整
  const viewportW = window.innerWidth;
  const viewportH = window.innerHeight;
  const bubbleW = 340; // 气泡预估宽度
  const bubbleH = 200; // 气泡预估高度

  let leftPx = left;
  let topPx = top;

  // 左右越界调整
  if (step.position === "bottom" || step.position === "top") {
    const minLeft = bubbleW / 2 + 16;
    const maxLeft = viewportW - bubbleW / 2 - 16;
    leftPx = Math.max(minLeft, Math.min(maxLeft, leftPx));
  } else if (step.position === "right") {
    if (leftPx + bubbleW > viewportW - 16) {
      // 空间不够，塞到上方或下方
      topPx = rect.bottom + offset + bubbleGap;
      leftPx = rect.left + rect.width / 2;
      transform = "translate(-50%, 0)";
    }
  }

  // 上下越界调整
  if (topPx + bubbleH > viewportH - 16) {
    topPx = viewportH - bubbleH - 16;
  }
  if (topPx < 16) {
    topPx = 16;
  }

  bubbleStyle.value = {
    top: `${topPx}px`,
    left: `${leftPx}px`,
    transform,
    opacity: 1,
  };
};

const handleNext = () => {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++;
  } else {
    handleClose();
  }
};

const handlePrev = () => {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
};

const handleClose = () => {
  emit("update:modelValue", false);
  localStorage.setItem("boss-helper:onboarding-completed", "true");
};

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      currentStep.value = 0;
      nextTick(() => {
        setTimeout(updatePosition, 100);
      });
    }
  }
);

watch(currentStep, () => {
  nextTick(updatePosition);
});

onMounted(() => {
  window.addEventListener("resize", updatePosition);
});

onUnmounted(() => {
  window.removeEventListener("resize", updatePosition);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[9995] transition-opacity duration-300 pointer-events-auto"
    >
      <!-- 暗色背景遮罩 -->
      <div class="absolute inset-0 bg-black/60 backdrop-blur-[2px]"></div>

      <!-- 探照灯聚光高亮区域 -->
      <div
        class="absolute border border-brand/50 rounded-xl transition-all duration-300 ease-out shadow-[0_0_24px_rgba(var(--accent-rgb),0.3),_0_0_0_9999px_rgba(0,0,0,0.5)] pointer-events-none z-[9996]"
        :style="highlightStyle"
      >
        <!-- 呼吸光环 -->
        <div class="absolute inset-0 rounded-xl animate-pulse-ring border-2 border-brand pointer-events-none"></div>
      </div>

      <!-- 导览详情气泡框 -->
      <div
        class="absolute w-[350px] rounded-2xl glass-surface p-5 z-[9997] transition-all duration-300 ease-out flex flex-col gap-4 text-fg"
        :style="bubbleStyle"
      >
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-semibold tracking-wider text-brand bg-brand/10 px-2 py-0.5 rounded-full">
            步骤 {{ currentStep + 1 }} / {{ steps.length }}
          </span>
          <button
            type="button"
            class="text-fg-subtle hover:text-fg text-xs transition-colors"
            @click="handleClose"
          >
            跳过指引
          </button>
        </div>

        <div class="flex flex-col gap-2">
          <h3 class="text-sm font-bold text-fg leading-snug">
            {{ steps[currentStep].title }}
          </h3>
          <p class="text-xs text-fg-muted whitespace-pre-wrap leading-relaxed">
            {{ steps[currentStep].desc }}
          </p>
        </div>

        <div class="flex items-center justify-between mt-2 pt-3 border-t border-bg-border/30">
          <div class="flex gap-1.5">
            <button
              v-if="currentStep > 0"
              type="button"
              class="btn-ghost !py-1 !px-2.5 !rounded-lg text-xs"
              @click="handlePrev"
            >
              上一步
            </button>
          </div>
          <button
            type="button"
            class="btn-primary !py-1 !px-3.5 !rounded-lg text-xs font-semibold"
            @click="handleNext"
          >
            {{ currentStep === steps.length - 1 ? "完成开启" : "下一步" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(var(--accent-rgb, 17, 24, 39), 0.4);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(var(--accent-rgb, 17, 24, 39), 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(var(--accent-rgb, 17, 24, 39), 0);
  }
}

.animate-pulse-ring {
  animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* 玻璃气泡框阴影样式微调，突出浮空感 */
.glass-surface {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(24px) saturate(140%);
  -webkit-backdrop-filter: blur(24px) saturate(140%);
  box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.4), inset 0 1px 0 var(--glass-highlight);
}
</style>
