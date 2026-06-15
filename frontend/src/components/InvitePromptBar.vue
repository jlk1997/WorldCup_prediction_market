<template>
  <div v-if="visible" class="invite-prompt-bar glass-inner">
    <div class="prompt-text">
      <strong>邀球友一起猜</strong>
      <span>双方得球迷币 · 冲召友周榜</span>
    </div>
    <div class="prompt-actions">
      <el-button type="primary" size="small" @click="openShare">去分享</el-button>
      <button type="button" class="dismiss-btn" aria-label="关闭" @click="dismiss">×</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { isLoggedIn } from '../stores/authStore'
import { useInviteShare } from '../composables/useInviteShare'

const props = defineProps<{
  scene: 'predict' | 'dashboard' | 'leaderboard'
}>()

const { openShareSheet } = useInviteShare()
const visible = ref(false)

const DISMISS_DAYS = 7

function storageKey() {
  return `wc2026_invite_prompt_dismiss_${props.scene}`
}

function isDismissed() {
  try {
    const raw = localStorage.getItem(storageKey())
    if (!raw) return false
    const ts = Number(raw)
    return Date.now() - ts < DISMISS_DAYS * 86400_000
  } catch {
    return false
  }
}

function syncVisible() {
  visible.value = isLoggedIn.value && !isDismissed()
}

watch(isLoggedIn, syncVisible, { immediate: true })

function dismiss() {
  visible.value = false
  try {
    localStorage.setItem(storageKey(), String(Date.now()))
  } catch {
    /* ignore */
  }
}

function openShare() {
  openShareSheet()
}
</script>

<style scoped>
.invite-prompt-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.28);
  background: rgba(212, 165, 116, 0.08);
}

.prompt-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.prompt-text strong {
  font-size: 0.88rem;
  color: #f5f0e8;
}

.prompt-text span {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.prompt-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.dismiss-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: var(--wc-text-muted);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}

.dismiss-btn:hover {
  color: #f5f0e8;
}
</style>
