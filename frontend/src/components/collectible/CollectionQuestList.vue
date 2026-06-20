<template>
  <div class="quest-list">
    <section v-if="daily.length">
      <div class="section-head">
        <h3>每日任务</h3>
        <span class="section-meta">{{ dailyDone }}/{{ daily.length }} 完成</span>
      </div>
      <div v-for="q in daily" :key="q.key" class="quest-row glass-inner" :class="{ done: q.completed }">
        <div class="quest-info">
          <p class="quest-title">{{ q.title }}</p>
          <div class="progress-wrap">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${questPct(q)}%` }" />
            </div>
            <span class="quest-progress">{{ q.progress }}/{{ q.target }}</span>
          </div>
        </div>
        <div class="quest-reward">
          <span class="xp-chip">+{{ q.xp }} XP</span>
          <el-tag v-if="q.completed" type="success" size="small" effect="plain">已完成</el-tag>
        </div>
      </div>
    </section>

    <section v-if="weekly.length">
      <div class="section-head">
        <h3>每周任务</h3>
        <span class="section-meta">{{ weeklyDone }}/{{ weekly.length }} 完成</span>
      </div>
      <div v-for="q in weekly" :key="q.key" class="quest-row glass-inner" :class="{ done: q.completed }">
        <div class="quest-info">
          <p class="quest-title">{{ q.title }}</p>
          <div class="progress-wrap">
            <div class="progress-bar">
              <div class="progress-fill weekly" :style="{ width: `${questPct(q)}%` }" />
            </div>
            <span class="quest-progress">{{ q.progress }}/{{ q.target }}</span>
          </div>
        </div>
        <div class="quest-reward">
          <span class="xp-chip weekly">+{{ q.xp }} XP</span>
          <el-tag v-if="q.completed" type="success" size="small" effect="plain">已完成</el-tag>
        </div>
      </div>
    </section>

    <p class="quest-hint">任务进度随玩法自动更新 · 完成后经验即时到账</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PassQuest } from '@/api/collectionPass'

const props = defineProps<{
  daily: PassQuest[]
  weekly: PassQuest[]
}>()

const dailyDone = computed(() => props.daily.filter((q) => q.completed).length)
const weeklyDone = computed(() => props.weekly.filter((q) => q.completed).length)

function questPct(q: PassQuest) {
  if (q.target <= 0) return 0
  return Math.min(100, Math.round((q.progress / q.target) * 100))
}
</script>

<style scoped>
.quest-list {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.section-head h3 {
  margin: 0;
  font-size: 0.88rem;
  color: #f5f0e8;
}

.section-meta {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.quest-list section {
  margin-bottom: 16px;
}

.quest-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  margin-bottom: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: opacity 0.2s;
}

.quest-row.done {
  opacity: 0.85;
}

.quest-info {
  flex: 1;
  min-width: 0;
}

.quest-title {
  margin: 0 0 8px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #f5f0e8;
}

.progress-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #7eb8ff, #5a9fd4);
  transition: width 0.35s ease;
}

.progress-fill.weekly {
  background: linear-gradient(90deg, #d4a574, #b8894a);
}

.quest-progress {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  white-space: nowrap;
}

.quest-reward {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.xp-chip {
  font-size: 0.72rem;
  font-weight: 700;
  color: #7eb8ff;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(126, 184, 255, 0.12);
}

.xp-chip.weekly {
  color: var(--wc-gold);
  background: rgba(212, 165, 116, 0.12);
}

.quest-hint {
  margin: 4px 0 0;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  text-align: center;
}
</style>
