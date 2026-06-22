<template>
  <div v-if="events.length" class="event-zone">
    <div v-for="ev in events" :key="ev.code" class="event-banner glass-panel">
      <div class="event-glow" aria-hidden="true" />

      <div class="event-content">
        <div class="event-head">
          <span class="event-tag">限时活动</span>
          <h3>{{ ev.name }}</h3>
          <span v-if="cheeredToday" class="done-tag">今日已完成</span>
        </div>

        <p v-if="ev.description" class="event-desc">{{ ev.description }}</p>

        <ul class="event-perks">
          <li>活动应援 {{ ev.coin_action_cost }} 球迷币 · 每日每队 1 次</li>
          <li>比赛日动员同样加权掉落限定卡</li>
        </ul>

        <div class="event-actions">
          <button
            v-if="cheeredToday"
            type="button"
            class="cheer-btn done"
            disabled
          >
            ✓ 今日已为{{ teamName }}应援
          </button>
          <button
            v-else
            type="button"
            class="cheer-btn"
            :disabled="!teamId || loading"
            @click="teamId && $emit('cheer', teamId)"
          >
            <span v-if="loading" class="btn-loading">应援中…</span>
            <span v-else-if="teamId">为{{ teamName }}应援 · {{ ev.coin_action_cost }} 币</span>
            <span v-else>设置主队后可应援</span>
          </button>
          <router-link v-if="!teamId" to="/onboarding" class="setup-link">去设置主队</router-link>
        </div>

        <p v-if="cheeredToday" class="done-hint">明日 0 点后可再次应援 · 掉落结果已记录</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import type { CollectibleEventBrief, EventCheerStatus } from '@/api/collectionPass'
import { authState } from '@/stores/authStore'
import { fetchProfileStatus, profileState } from '@/stores/profileStore'

const props = defineProps<{
  events?: CollectibleEventBrief[] | null
  event?: CollectibleEventBrief | null
  loading?: boolean
  cheerStatus?: EventCheerStatus | null
}>()

defineEmits<{ cheer: [teamId: number] }>()

const events = computed(() => {
  if (props.events?.length) return props.events
  if (props.event) return [props.event]
  return []
})

const teamId = computed(() => props.cheerStatus?.team_id ?? authState.user?.favorite_team_id ?? null)
const teamName = computed(
  () => props.cheerStatus?.team_name || profileState.status?.main_team?.name || '主队',
)
const cheeredToday = computed(() => props.cheerStatus?.cheered_today === true)

onMounted(() => {
  if (teamId.value) void fetchProfileStatus()
})
</script>

<style scoped>
.event-zone {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.event-banner {
  position: relative;
  overflow: hidden;
  padding: 0;
  border: 1px solid rgba(126, 184, 255, 0.35);
  border-radius: 14px;
  background: rgba(8, 12, 28, 0.92) !important;
}

.event-glow {
  position: absolute;
  inset: -40% -20% auto auto;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(126, 184, 255, 0.22), transparent 70%);
  pointer-events: none;
}

.event-content {
  position: relative;
  padding: 14px 16px;
}

.event-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

.event-tag {
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(126, 184, 255, 0.2);
  color: #9ec8ff;
  font-weight: 600;
}

.done-tag {
  font-size: 0.62rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(95, 200, 143, 0.18);
  color: #7dd3a8;
  font-weight: 600;
  margin-left: auto;
}

.event-head h3 {
  margin: 0;
  font-size: 1.02rem;
  color: #f5f0e8;
}

.event-desc {
  margin: 0 0 8px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.45;
}

.event-perks {
  margin: 0 0 12px;
  padding-left: 1.1em;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.5;
}

.event-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.cheer-btn {
  flex: 1;
  min-width: 160px;
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, #e8c88a 0%, #c99850 100%);
  color: #1a1208;
  box-shadow: 0 4px 16px rgba(212, 165, 116, 0.35);
  transition: transform 0.12s, opacity 0.12s;
}
.cheer-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.cheer-btn:disabled:not(.done) {
  opacity: 0.55;
  cursor: not-allowed;
}
.cheer-btn.done {
  background: rgba(95, 200, 143, 0.15);
  color: #7dd3a8;
  border: 1px solid rgba(125, 211, 168, 0.35);
  box-shadow: none;
  cursor: default;
}

.btn-loading {
  opacity: 0.85;
}

.done-hint {
  margin: 10px 0 0;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.45);
}

.setup-link {
  font-size: 0.78rem;
  color: #9ec8ff;
  text-decoration: none;
}
.setup-link:hover {
  text-decoration: underline;
}
</style>
