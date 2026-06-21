<template>
  <div v-if="visible" class="rate-limit-banner" role="status" aria-live="polite">
    <span class="rate-limit-banner-icon" aria-hidden="true">⏳</span>
    <span class="rate-limit-banner-text">
      <template v-if="detailMessage">{{ detailMessage }}</template>
      <template v-else>
        操作过于频繁，请 <strong>{{ remainingSec }}</strong> 秒后再试
      </template>
      <span v-if="detailMessage" class="countdown">（{{ remainingSec }} 秒后可继续）</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getLastRateLimitMessage, getRateLimitRemainingMs, isRateLimited } from '../api/rateLimitGuard'

const tick = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const remainingSec = computed(() => {
  void tick.value
  return Math.max(1, Math.ceil(getRateLimitRemainingMs() / 1000))
})

const detailMessage = computed(() => {
  void tick.value
  return getLastRateLimitMessage()
})

const visible = computed(() => {
  void tick.value
  return isRateLimited()
})

onMounted(() => {
  timer = setInterval(() => {
    tick.value += 1
  }, 500)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.rate-limit-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 8px 16px;
  padding-top: max(8px, env(safe-area-inset-top, 0px));
  background: rgba(212, 165, 116, 0.18);
  border-bottom: 1px solid rgba(212, 165, 116, 0.35);
  color: #f5e6c8;
  font-size: 0.85rem;
  line-height: 1.4;
  z-index: 1200;
}

.rate-limit-banner-icon {
  flex-shrink: 0;
}

.rate-limit-banner-text strong {
  color: var(--wc-accent-gold, #d4a574);
  font-weight: 700;
  min-width: 1.5em;
  display: inline-block;
  text-align: center;
}

.countdown {
  opacity: 0.85;
  margin-left: 4px;
  white-space: nowrap;
}
</style>
