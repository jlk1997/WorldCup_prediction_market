<template>
  <div v-if="items.length" class="rec-bar glass-panel">
    <span class="label">为你推荐</span>
    <div class="chips">
      <button
        v-for="c in items"
        :key="c.path + c.label"
        type="button"
        class="chip"
        :class="[c.type, { primary: c.primary }]"
        @click="go(c)"
      >
        {{ c.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { profileState } from '../stores/profileStore'
import type { DailyStatus } from '../api/commerce'
import { navigateDailyAction } from '../utils/dailyActionNav'

const props = defineProps<{
  max?: number
  dailyStatus?: DailyStatus | null
}>()
const router = useRouter()
const route = useRoute()

const items = computed(() => {
  const list: Array<{ label: string; path: string; type?: string; primary?: boolean; key?: string }> = []
  const next = props.dailyStatus?.next_action
  if (next?.path && next.key !== 'done') {
    list.push({
      label: next.label,
      path: next.path,
      key: next.key,
      type: 'next',
      primary: true,
    })
  }
  const cta = profileState.recommendations?.cta ?? []
  const limit = props.max ?? 4
  for (const c of cta) {
    if (list.length >= limit) break
    if (next?.path && c.path === next.path) continue
    list.push(c)
  }
  return list.slice(0, limit)
})

function go(item: { path: string; key?: string; label?: string }) {
  if (item.key) {
    navigateDailyAction(router, route, { key: item.key, path: item.path, label: item.label })
    return
  }
  router.push(item.path)
}
</script>

<style scoped>
.rec-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.label {
  font-size: 0.8rem;
  color: var(--wc-accent-gold);
  font-weight: 600;
  flex-shrink: 0;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.08);
  color: var(--wc-text-primary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}
.chip:hover {
  background: rgba(212, 165, 116, 0.18);
  transform: translateY(-1px);
}
.chip.primary {
  border-color: var(--wc-accent-gold, #d4a574);
  background: rgba(212, 165, 116, 0.22);
  font-weight: 600;
}
.chip.next { border-color: rgba(103, 194, 58, 0.45); }
.chip.cheer { border-color: rgba(139, 41, 66, 0.5); }
.chip.onboarding { border-color: rgba(201, 120, 138, 0.5); }
</style>
