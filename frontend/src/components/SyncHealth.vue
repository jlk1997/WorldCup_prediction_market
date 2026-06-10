<template>
  <div class="sync-health glass-panel" :class="{ compact }">
    <span class="title">自动同步</span>
    <span class="hint">后台定时更新，无需手动操作</span>
    <template v-if="logs.length">
      <span v-for="log in logs.slice(0, 3)" :key="log.source + String(log.ran_at)" class="log-item">
        {{ log.source }}: <strong :class="log.status">{{ log.status }}</strong> ({{ log.records }})
      </span>
    </template>
    <span v-else class="hint">等待首次同步…</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { apiClient } from '@/api/client'

interface SyncLog {
  source: string
  status: string
  records: number
  error?: string
  ran_at?: string
}

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })

const logs = ref<SyncLog[]>([])
let timer: ReturnType<typeof setInterval> | null = null

async function loadLogs() {
  try {
    const res = await apiClient.get<{ logs: SyncLog[] }>('/api/sync/status')
    logs.value = res.data.logs || []
  } catch {
    logs.value = []
  }
}

onMounted(() => {
  loadLogs()
  timer = setInterval(loadLogs, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.sync-health {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 8px 14px;
  margin-bottom: 12px;
  font-size: 0.78rem;
  color: #c9d1d9;
  background: var(--wc-bg-panel);
  backdrop-filter: blur(10px);
  border: 1px solid var(--wc-border-soft);
  border-radius: var(--wc-radius-sm);
}
.sync-health:not(.compact) {
  position: absolute;
  top: 12px;
  left: 24px;
  z-index: 30;
  padding: 4px 12px;
  font-size: 0.7rem;
  margin-bottom: 0;
  pointer-events: auto;
  max-width: calc(100% - 48px);
}
.title { color: var(--wc-accent-gold-light); font-weight: bold; }
.hint { color: var(--wc-text-muted); }
.log-item { color: #c9d1d9; }
.log-item strong.ok { color: #67c23a; }
.log-item strong.skipped { color: #909399; }
.log-item strong.partial { color: #e6a23c; }

@media (max-width: 768px) {
  .sync-health:not(.compact) {
    left: 8px;
    right: 8px;
    max-width: calc(100% - 16px);
    font-size: 0.65rem;
    gap: 6px;
    top: 8px;
  }
  .sync-health.compact {
    font-size: 0.72rem;
    gap: 8px;
  }
}
</style>
