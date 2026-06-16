<template>
  <div
    v-if="visible"
    class="qq-social-bar glass-inner"
    role="button"
    tabindex="0"
    @click="openModal"
    @keydown.enter="openModal"
  >
    <span class="qq-icon" aria-hidden="true">💬</span>
    <div class="qq-text">
      <strong>{{ officialQqGroupConfig.group_name || '官方 QQ 群' }}</strong>
      <span>{{ subline }}</span>
    </div>
    <span class="qq-cta">领 {{ officialQqGroupConfig.reward_coins }} 币 →</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isLoggedIn } from '@/stores/authStore'
import {
  officialQqGroupConfig,
  officialQqGroupState,
  openOfficialQqGroupModal,
} from '@/composables/useOfficialQqGroup'

const props = withDefaults(
  defineProps<{
    /** 比赛日强化文案 */
    matchDay?: boolean
    /** 今日全站签到人数（社群压力） */
    todaySigninCount?: number
  }>(),
  { matchDay: false, todaySigninCount: 0 },
)

const visible = computed(
  () =>
    officialQqGroupConfig.enabled &&
    isLoggedIn.value &&
    !officialQqGroupState.claimed,
)

const subline = computed(() => {
  const n = props.todaySigninCount
  if (n > 0) {
    const base = `今日已有 ${n} 位球友签到`
    return props.matchDay ? `${base} · 比赛日球友都在聊` : `${base} · 加群一起猜`
  }
  if (props.matchDay) {
    return '比赛日球友都在聊 · 加群领币一起看球猜球'
  }
  return '加群领球迷币 · 比赛日一起看球猜球'
})

function openModal() {
  openOfficialQqGroupModal()
}
</script>

<style scoped>
.qq-social-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 12px;
  border: 1px solid rgba(88, 166, 255, 0.35);
  background: rgba(88, 166, 255, 0.08);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.qq-social-bar:hover {
  border-color: rgba(88, 166, 255, 0.55);
  background: rgba(88, 166, 255, 0.12);
}

.qq-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.qq-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.qq-text strong {
  font-size: 0.86rem;
  color: #f5f0e8;
}

.qq-text span {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.qq-cta {
  flex-shrink: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: #58a6ff;
}
</style>
