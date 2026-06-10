<template>
  <div class="events-timeline" v-if="events.length">
    <h4 v-if="title">{{ title }}</h4>
    <div v-for="(ev, i) in events" :key="i" class="event-row" :class="eventClass(ev)">
      <span class="min">{{ ev.minute }}'</span>
      <span class="type">{{ eventLabel(ev) }}</span>
      <span class="who">{{ ev.player || ev.team }}</span>
    </div>
  </div>
  <p v-else-if="showEmpty" class="empty">{{ emptyText }}</p>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MatchEvent } from '@/types/api'

const props = withDefaults(
  defineProps<{
    items?: MatchEvent[] | unknown
    title?: string
    showEmpty?: boolean
    emptyText?: string
  }>(),
  { showEmpty: false, emptyText: '暂无比赛事件' }
)

const events = computed(() => {
  if (!props.items) return []
  if (Array.isArray(props.items)) return props.items as MatchEvent[]
  return []
})

function eventLabel(ev: MatchEvent) {
  const t = (ev.type || ev.detail || '').toLowerCase()
  if (t.includes('goal')) return '⚽ 进球'
  if (t.includes('card') || t.includes('yellow')) return '🟨 黄牌'
  if (t.includes('red')) return '🟥 红牌'
  if (t.includes('subst')) return '🔄 换人'
  return ev.type || ev.detail || '事件'
}

function eventClass(ev: MatchEvent) {
  const t = (ev.type || '').toLowerCase()
  if (t.includes('goal')) return 'goal'
  if (t.includes('red')) return 'red'
  return ''
}
</script>

<style scoped>
.events-timeline { font-size: 0.8rem; }
.events-timeline h4 { margin: 0 0 8px; color: #D2A76D; font-size: 0.85rem; }
.event-row { display: flex; gap: 10px; padding: 4px 0; border-bottom: 1px dashed rgba(255,255,255,0.06); }
.event-row.goal { color: #D2A76D; }
.event-row.red { color: #f56c6c; }
.min { width: 32px; color: #6e7681; }
.type { width: 72px; }
.who { flex: 1; }
.empty { color: #6e7681; font-size: 0.8rem; }
</style>
