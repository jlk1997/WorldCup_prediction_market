<template>
  <section v-if="data?.acts?.length" class="season-narrative glass-panel">
    <header class="sn-head">
      <h3>赛季三幕 · 收藏叙事</h3>
      <span class="sn-act">{{ actTitle }}</span>
    </header>
    <div v-for="act in data.acts" :key="act.act" class="sn-row">
      <div class="sn-label">{{ act.title }}</div>
      <div class="sn-bar">
        <div class="sn-fill" :style="{ width: `${act.progress_pct}%` }" />
      </div>
      <span class="sn-meta">{{ act.cards_owned }}/{{ act.cards_total }}</span>
    </div>
    <p class="sn-hint">集齐系列解锁手册等级与下季联名优先权（站内体验）</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient } from '@/api/client'
import { authState } from '@/stores/authStore'

interface ActRow {
  act: string
  title: string
  cards_total: number
  cards_owned: number
  progress_pct: number
}

const data = ref<{ acts: ActRow[]; current_act: string } | null>(null)

const actTitle = computed(() => {
  const map: Record<string, string> = {
    group_stage: '第一幕 · 小组赛',
    knockout: '第二幕 · 淘汰赛',
    final: '第三幕 · 决赛周',
  }
  return map[data.value?.current_act || ''] || '世界杯2026'
})

onMounted(async () => {
  if (!authState.user) return
  try {
    const res = await apiClient.get('/api/game/season-narrative')
    data.value = res.data
  } catch {
    data.value = null
  }
})
</script>

<style scoped>
.season-narrative {
  margin: 12px 0;
  padding: 14px 16px;
}
.sn-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.sn-head h3 {
  margin: 0;
  font-size: 0.95rem;
}
.sn-act {
  font-size: 0.72rem;
  color: var(--wc-accent-gold);
}
.sn-row {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.78rem;
}
.sn-bar {
  height: 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.sn-fill {
  height: 100%;
  background: linear-gradient(90deg, #d4a574, #a371f7);
}
.sn-meta {
  color: var(--wc-text-muted);
  font-size: 0.7rem;
}
.sn-hint {
  margin: 8px 0 0;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
</style>
