<script setup lang="ts">
/**
 * SponsorPanel — 顶栏咖啡杯按钮 + 玻璃态打赏弹窗
 * 替换原来的左下角固定卡片，更符合 Bangumi-syncer 的打赏入口交互
 */
import { ref, onMounted } from "vue";

interface Thanks {
  id: string;
  name: string;
  amount?: string;
  message?: string;
  created_at: string;
}

interface QRCodeUrls {
  wechat?: string;
  alipay?: string;
}

const qrCodes = ref<QRCodeUrls>({});
const thanksList = ref<Thanks[]>([]);
const isLoading = ref(true);
const showModal = ref(false);
const activeQr = ref<"wechat" | "alipay">("wechat");

onMounted(async () => {
  await Promise.all([loadQRCodes(), loadThanks()]);
  isLoading.value = false;
});

async function loadQRCodes() {
  try {
    const res = await fetch("/api/sponsor/qrcode");
    if (res.ok) {
      qrCodes.value = await res.json();
    }
  } catch (e) {
    console.error("加载收款码失败:", e);
  }
}

async function loadThanks() {
  try {
    const res = await fetch("/api/sponsor/thanks");
    if (res.ok) {
      const data = await res.json();
      thanksList.value = data.thanks || [];
    }
  } catch (e) {
    console.error("加载鸣谢列表失败:", e);
  }
}

function openModal(type: "wechat" | "alipay") {
  activeQr.value = type;
  showModal.value = true;
}

function formatDate(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("zh-CN");
  } catch {
    return dateStr;
  }
}
</script>

<template>
  <!-- 顶栏咖啡杯按钮 -->
  <button
    class="relative w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 text-fg-muted hover:text-fg hover:bg-bg-raised"
    title="支持一下 ☕"
    @click="showModal = true"
  >
    <!-- Coffee cup SVG -->
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M17 8h1a4 4 0 0 1 0 8h-1" />
      <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
      <line x1="6" x2="6" y1="2" y2="4" />
      <line x1="10" x2="10" y1="2" y2="4" />
      <line x1="14" x2="14" y1="2" y2="4" />
    </svg>
  </button>

  <!-- 打赏弹窗 -->
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="showModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        @click.self="showModal = false"
      >
        <div
          class="relative w-[420px] max-w-[calc(100vw-2rem)] rounded-2xl glass-surface overflow-hidden"
          @click.stop
        >
          <!-- 顶部渐变装饰条 -->
          <div class="h-1.5 bg-gradient-to-r from-amber-400 via-rose-400 to-violet-400" />

          <!-- 头部 -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-glass-border">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-center justify-center">
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
                  class="text-amber-500"
                >
                  <path d="M17 8h1a4 4 0 0 1 0 8h-1" />
                  <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
                </svg>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-fg">支持一下</h3>
                <p class="text-[11px] text-fg-subtle">您的支持是我最大的动力</p>
              </div>
            </div>
            <button
              class="w-8 h-8 rounded-lg flex items-center justify-center text-fg-subtle hover:text-fg hover:bg-bg-raised transition-colors"
              @click="showModal = false"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- 收款码切换区 -->
          <div class="px-5 pt-4">
            <div v-if="!isLoading" class="grid grid-cols-2 gap-3">
              <!-- 微信 -->
              <button
                v-if="qrCodes.wechat"
                class="flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200"
                :class="
                  activeQr === 'wechat'
                    ? 'bg-green-50 dark:bg-green-950/30 border-2 border-green-400 dark:border-green-600'
                    : 'bg-bg-raised border border-glass-border hover:border-green-400/50'
                "
                @click="openModal('wechat')"
              >
                <span class="text-3xl">💚</span>
                <div class="text-center">
                  <p class="text-sm font-medium text-fg">微信</p>
                  <p class="text-[10px] text-fg-subtle mt-0.5">WeChat Pay</p>
                </div>
              </button>

              <!-- 支付宝 -->
              <button
                v-if="qrCodes.alipay"
                class="flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200"
                :class="
                  activeQr === 'alipay'
                    ? 'bg-blue-50 dark:bg-blue-950/30 border-2 border-blue-400 dark:border-blue-600'
                    : 'bg-bg-raised border border-glass-border hover:border-blue-400/50'
                "
                @click="openModal('alipay')"
              >
                <span class="text-3xl">💙</span>
                <div class="text-center">
                  <p class="text-sm font-medium text-fg">支付宝</p>
                  <p class="text-[10px] text-fg-subtle mt-0.5">Alipay</p>
                </div>
              </button>

              <!-- 无收款码 -->
              <div
                v-if="!qrCodes.wechat && !qrCodes.alipay"
                class="col-span-2 flex flex-col items-center justify-center py-10 gap-3 rounded-xl bg-bg-raised border border-glass-border"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="text-fg-subtle"
                >
                  <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                  <circle cx="9" cy="9" r="2" />
                  <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                </svg>
                <p class="text-sm text-fg-subtle">暂未配置收款码</p>
              </div>
            </div>

            <!-- 加载中 -->
            <div v-else class="flex items-center justify-center py-10">
              <div class="w-5 h-5 border-2 border-brand/30 border-t-brand rounded-full animate-spin" />
            </div>
          </div>

          <!-- 收款码大图 -->
          <div v-if="qrCodes[activeQr]" class="px-5 pt-3">
            <div class="aspect-square rounded-xl bg-bg-raised border border-glass-border flex items-center justify-center overflow-hidden p-4">
              <img
                :src="qrCodes[activeQr]"
                :alt="activeQr === 'wechat' ? '微信收款码' : '支付宝收款码'"
                class="max-w-full max-h-full object-contain rounded-lg"
              />
            </div>
            <p class="text-center text-xs text-fg-subtle mt-2.5">
              识别二维码，转账支持 · 金额随意，心意至上
            </p>
          </div>

          <!-- 鸣谢列表 -->
          <div class="px-5 pt-4 pb-5">
            <div class="border-t border-glass-border pt-4">
              <div class="flex items-center gap-2 mb-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  stroke="none"
                  class="text-rose-400"
                >
                  <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
                </svg>
                <h4 class="text-xs font-semibold text-fg">鸣谢列表</h4>
                <span class="text-[10px] text-fg-subtle ml-auto">{{ thanksList.length }} 人支持</span>
              </div>

              <div v-if="thanksList.length > 0" class="space-y-2">
                <div
                  v-for="t in thanksList.slice(0, 8)"
                  :key="t.id"
                  class="flex items-center gap-2.5 py-1.5"
                >
                  <div class="w-6 h-6 rounded-full bg-rose-100 dark:bg-rose-950/40 flex items-center justify-center text-[10px] font-bold text-rose-500">
                    {{ t.name.slice(0, 1) }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-xs text-fg font-medium truncate">{{ t.name }}</p>
                    <p v-if="t.message" class="text-[10px] text-fg-subtle truncate">{{ t.message }}</p>
                  </div>
                  <div class="shrink-0 text-right">
                    <p v-if="t.amount" class="text-[10px] font-medium text-amber-500">{{ t.amount }}</p>
                    <p class="text-[9px] text-fg-subtle">{{ formatDate(t.created_at) }}</p>
                  </div>
                </div>
              </div>

              <div
                v-else
                class="flex flex-col items-center justify-center py-6 gap-2 rounded-xl bg-bg-raised/50"
              >
                <p class="text-xs text-fg-subtle">暂无鸣谢，成为第一位支持者</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
}
</style>
