<template>
  <el-drawer
    v-model="open"
    direction="btt"
    size="82%"
    :title="title"
    append-to-body
    destroy-on-close
    :close-on-click-modal="true"
    class="mobile-schedule-drawer"
  >
    <div class="mobile-schedule-list">
      <div
        v-for="match in matches"
        :key="match.id ?? `${match.team1}-${match.team2}`"
        class="grid-card glass-panel"
        @click="onSelect(match)"
      >
        <div class="card-header">
          <span class="card-group">{{ match.group }}</span>
          <span class="card-time">{{ match.time }}</span>
        </div>
        <div class="card-teams">
          <span class="t-name">{{ match.team1 }}</span>
          <span v-if="match.home_score != null" class="t-score">{{ match.home_score }}:{{ match.away_score }}</span>
          <span v-else class="t-vs">vs</span>
          <span class="t-name">{{ match.team2 }}</span>
        </div>
        <div class="card-footer">{{ match.date }} · {{ match.stadium }}</div>
      </div>
    </div>
    <template #footer>
      <el-button type="primary" class="close-btn" @click="open = false">收起赛程</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import type { ScheduleItem } from '../types/api'

const open = defineModel<boolean>({ default: false })

defineProps<{
  matches: ScheduleItem[]
  title?: string
}>()

const emit = defineEmits<{ select: [match: ScheduleItem] }>()

function onSelect(match: ScheduleItem) {
  emit('select', match)
  open.value = false
}
</script>

<style scoped>
.mobile-schedule-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 8px;
}

.grid-card {
  padding: 12px 14px;
  cursor: pointer;
}

.card-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  margin-bottom: 6px;
}

.card-group {
  color: var(--wc-accent-gold);
  font-weight: 600;
}

.card-teams {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 700;
  font-size: 0.95rem;
}

.t-vs {
  color: var(--wc-text-muted);
  font-size: 0.8rem;
}

.card-footer {
  margin-top: 6px;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  text-align: center;
}

.close-btn {
  width: 100%;
  min-height: 44px;
}
</style>

<style>
.mobile-schedule-drawer.el-drawer {
  background: rgba(14, 16, 32, 0.98) !important;
}

.mobile-schedule-drawer .el-drawer__header {
  margin-bottom: 8px;
  padding: 16px 16px 8px;
  border-bottom: 1px solid rgba(212, 165, 116, 0.15);
}

.mobile-schedule-drawer .el-drawer__title {
  color: #f5f0e8;
  font-weight: 700;
}

.mobile-schedule-drawer .el-drawer__close-btn {
  width: 36px;
  height: 36px;
  font-size: 18px;
}

.mobile-schedule-drawer .el-drawer__body {
  padding: 12px 16px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.mobile-schedule-drawer .el-drawer__footer {
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
