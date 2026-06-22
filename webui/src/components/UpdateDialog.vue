<script setup lang="ts">
import { ref, onMounted } from "vue";

interface VersionInfo {
  current_version: string;
  has_update: boolean;
  version: string;
  release_date: string;
  changelog: string;
  download_url: string;
  is_mandatory: boolean;
}

const props = defineProps<{
  info: VersionInfo;
}>();

const emit = defineEmits<{
  close: [];
}>();

const showModal = ref(true);

// 切换 changelog 展开
const expanded = ref(false);

function handleClose() {
  showModal.value = false;
  emit("close");
}

function openDownload() {
  if (props.info.download_url) {
    window.open(props.info.download_url, "_blank");
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="showModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <div class="relative bg-bg-panel rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        <!-- 顶部装饰条 -->
        <div class="h-1.5 bg-gradient-to-r from-brand via-pink-400 to-yellow-400"></div>

        <!-- 头部 -->
        <div class="p-6 pb-4">
          <div class="flex items-start justify-between">
            <div>
              <h2 class="text-lg font-semibold text-fg flex items-center gap-2">
                <span>🚀</span>
                <span>发现新版本</span>
              </h2>
              <p class="mt-1 text-sm text-fg-subtle">
                v{{ info.version }}
                <template v-if="info.release_date">
                  · {{ info.release_date }}
                </template>
              </p>
            </div>
            <button
              class="w-8 h-8 rounded-full flex items-center justify-center text-fg-subtle hover:text-fg hover:bg-bg-raised transition-colors"
              @click="handleClose"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- 更新内容 -->
        <div class="px-6 pb-4">
          <div class="bg-bg-raised rounded-xl p-4 max-h-48 overflow-y-auto">
            <button
              class="w-full flex items-center justify-between text-sm text-fg-muted mb-2"
              @click="expanded = !expanded"
            >
              <span>更新日志</span>
              <span
                class="transition-transform duration-200"
                :class="expanded ? 'rotate-180' : ''"
              >
                ▼
              </span>
            </button>

            <div v-if="expanded" class="text-xs text-fg-muted whitespace-pre-wrap">
              {{ info.changelog }}
            </div>
            <div v-else class="text-xs text-fg-subtle">
              点击展开查看更新内容
            </div>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="px-6 pb-6 flex gap-3">
          <button
            class="flex-1 py-2.5 rounded-xl text-sm font-medium bg-bg-raised text-fg-muted hover:bg-bg-border transition-colors"
            @click="handleClose"
          >
            稍后再说
          </button>
          <button
            class="flex-1 py-2.5 rounded-xl text-sm font-medium bg-brand text-bg-base hover:opacity-90 transition-opacity"
            @click="openDownload"
          >
            前往下载
          </button>
        </div>

        <!-- 强制更新提示 -->
        <div
          v-if="info.is_mandatory"
          class="px-6 pb-4"
        >
          <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-3 text-xs text-yellow-700 dark:text-yellow-300">
            ⚠️ 此版本为强制更新，请尽快升级以继续使用
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
