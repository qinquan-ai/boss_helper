<script setup lang="ts">
import { computed } from "vue";
import { useEngine } from "@/stores/engine";

const engine = useEngine();

const meta = computed(() => {
  const kind = engine.pendingAction?.kind || "confirm";
  return (
    {
      captcha: { icon: "🛡️", title: "需要完成验证码", accent: "text-amber-500" },
      login: { icon: "🔑", title: "登录可能已失效", accent: "text-rose-500" },
      page_check: { icon: "🧭", title: "请确认页面状态", accent: "text-fg" },
      confirm: { icon: "❓", title: "需要确认", accent: "text-fg" },
    } as Record<string, { icon: string; title: string; accent: string }>
  )[kind];
});

const isPageCheck = computed(() => engine.pendingAction?.kind === "page_check");
</script>

<template>
  <transition name="fade">
    <div
      v-if="engine.pendingAction"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
    >
      <div class="card p-6 w-[440px] shadow-glow animate-fade-in">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ meta.icon }}</span>
          <div class="flex-1">
            <h3 class="text-base font-semibold" :class="meta.accent">{{ meta.title }}</h3>
            <p class="mt-2 text-sm text-fg-muted whitespace-pre-wrap leading-relaxed">
              {{ engine.pendingAction.reason }}
            </p>
            <p class="mt-3 text-xs text-fg-subtle">
              请切换到浏览器窗口完成操作，处理好后点击下方按钮继续。
            </p>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            v-if="isPageCheck"
            class="btn-ghost"
            @click="engine.ack('wait')"
          >
            我要先手动操作
          </button>
          <button class="btn-primary" @click="engine.ack('')">我已完成，继续</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
