<template>
  <div v-if="status" class="daily-ritual">
    <div class="ritual-head glass-inner">
      <div class="progress-ring">
        <el-progress
          type="circle"
          :percentage="status.ritual_progress?.pct ?? 0"
          :width="52"
          :stroke-width="5"
          color="var(--wc-accent-gold, #d4a574)"
        />
        <span class="progress-label">{{ status.ritual_progress?.done ?? 0 }}/{{ status.ritual_progress?.total ?? 3 }}</span>
      </div>
      <div class="ritual-main">
        <div class="ritual-title">
          <span v-if="status.match_day" class="match-day-tag">比赛日</span>
          <span v-if="status.signin_streak >= 1">🔥 连签 {{ status.signin_streak }} 天</span>
          <span v-if="status.win_streak >= 2"> · 连胜 {{ status.win_streak }}</span>
        </div>
        <button
          v-if="status.next_action"
          type="button"
          class="next-action"
          @click="goNext"
        >
          <span class="next-label">{{ status.next_action.label }}</span>
          <span v-if="status.next_action.hint" class="next-hint">{{ status.next_action.hint }}</span>
          <span class="next-arrow" aria-hidden="true">→</span>
        </button>
      </div>
      <el-button
        v-if="showSignin && !status.signed_today"
        size="small"
        type="warning"
        :loading="signing"
        @click="$emit('signin')"
      >
        签到领币
      </el-button>
    </div>

    <div v-if="status.checklist?.length" class="checklist">
      <div
        v-for="item in status.checklist.filter((c) => !c.optional)"
        :key="item.key"
        class="check-item"
        :class="{ done: item.done, clickable: !item.done }"
        @click="onCheckItem(item)"
      >
        <span class="check-icon">{{ item.done ? '✓' : '○' }}</span>
        <span class="check-label">{{ item.label }}</span>
        <span class="check-reward">{{ item.reward }}</span>
      </div>
    </div>

    <div v-if="status.redeem_progress && status.redeem_progress.gap > 0" class="redeem-row">
      <el-progress
        :percentage="status.redeem_progress.pct"
        :stroke-width="8"
        style="flex: 1"
      />
      <span class="redeem-gap">
        差 {{ status.redeem_progress.gap }} 分换 {{ status.redeem_progress.next_name }}
        <template v-if="status.redeem_progress.wins_estimate">
          · 约 {{ status.redeem_progress.wins_estimate }} 场
        </template>
      </span>
    </div>

    <el-alert
      v-if="status.match_day_message"
      type="success"
      :closable="true"
      show-icon
      class="ritual-alert"
      :title="status.match_day_message"
    />
    <button
      v-if="status.streak_risk"
      type="button"
      class="streak-risk-alert"
      @click="goStreakProtect"
    >
      <el-alert
        type="warning"
        :closable="false"
        class="ritual-alert ritual-alert--click"
        :title="status.streak_risk.message"
      />
    </button>
    <el-alert
      v-else-if="showLossHint"
      type="info"
      :closable="true"
      class="ritual-alert"
      title="连败保护已就绪"
      description="下次猜中积分有额外加成"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { DailyStatus } from '../api/commerce'
import { navigateDailyAction } from '../utils/dailyActionNav'
import { openOfficialQqGroupModal } from '../composables/useOfficialQqGroup'

const props = defineProps<{
  status: DailyStatus | null
  showSignin?: boolean
  signing?: boolean
}>()

defineEmits<{ signin: [] }>()

const router = useRouter()
const route = useRoute()

const showLossHint = computed(() => {
  const s = props.status
  if (!s?.loss_streak) return false
  const after = s.loss_streak_protect_after ?? 3
  return s.loss_streak >= after
})

function goNext() {
  navigateDailyAction(router, route, props.status?.next_action ?? null)
}

function goStreakProtect() {
  const mid = props.status?.streak_risk?.match_id
  router.push(mid ? { path: '/predict', query: { highlight: String(mid) } } : '/predict')
}

function onCheckItem(item: { key: string; done: boolean }) {
  if (item.done) return
  if (item.key === 'qq_group') {
    openOfficialQqGroupModal()
    return
  }
  if (item.key === 'quiz' || item.key === 'signin' || item.key === 'pending') {
    navigateDailyAction(router, route, { key: item.key, path: `/me?focus=${item.key === 'pending' ? 'predictions' : item.key}` })
    return
  }
  if (item.key === 'predict') router.push('/predict')
}
</script>

<style scoped>
.daily-ritual {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ritual-head {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  flex-wrap: wrap;
}

.progress-ring {
  position: relative;
  flex-shrink: 0;
}

.progress-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--wc-text-muted, #9a94a8);
}

.ritual-main {
  flex: 1;
  min-width: 160px;
}

.ritual-title {
  font-size: 13px;
  margin-bottom: 6px;
}

.match-day-tag {
  display: inline-block;
  margin-right: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
  font-size: 11px;
  font-weight: 600;
}

.next-action {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.25);
  background: rgba(212, 165, 116, 0.06);
  cursor: pointer;
  text-align: left;
  width: 100%;
  box-sizing: border-box;
}

.next-action:hover {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.1);
}

.next-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--wc-text-primary, #eee);
  flex: 1;
  min-width: 0;
}

.next-hint {
  font-size: 12px;
  color: var(--wc-text-muted, #9a94a8);
  width: 100%;
}

.next-arrow {
  font-size: 16px;
  font-weight: 700;
  color: var(--wc-accent-gold, #d4a574);
  flex-shrink: 0;
}

.streak-risk-alert {
  display: block;
  width: 100%;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
}

.ritual-alert--click {
  margin: 0;
  pointer-events: none;
}

.checklist {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 4px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 16px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  opacity: 0.65;
}

.check-item.clickable {
  cursor: pointer;
}

.check-item.clickable:hover {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.08);
}

.check-item.done {
  opacity: 1;
  border-color: rgba(103, 194, 58, 0.35);
}

.check-icon {
  font-size: 11px;
}

.check-reward {
  color: var(--wc-text-muted, #9a94a8);
}

.redeem-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 4px;
  font-size: 12px;
}

.redeem-gap {
  flex-shrink: 0;
  color: var(--wc-accent-rose, #c9788a);
}

.ritual-alert {
  margin: 0;
}
</style>
