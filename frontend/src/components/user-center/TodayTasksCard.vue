<template>
  <div class="today-tasks glass-panel">
    <div class="tasks-head">
      <div class="progress-ring">
        <el-progress
          type="circle"
          :percentage="status?.ritual_progress?.pct ?? 0"
          :width="56"
          :stroke-width="5"
          color="var(--wc-accent-gold, #d4a574)"
        />
        <span class="progress-label">已完成 {{ status?.ritual_progress?.done ?? 0 }}/{{ status?.ritual_progress?.total ?? 3 }}</span>
      </div>
      <div class="tasks-main">
        <div class="tasks-title">
          <span v-if="status?.match_day" class="match-day-tag">比赛日</span>
          <span>今日任务</span>
          <span v-if="status && status.signin_streak >= 1" class="streak-hint"> · 连签 {{ status.signin_streak }} 天</span>
        </div>
        <button
          v-if="status?.next_action"
          type="button"
          class="main-cta"
          @click="goNext"
        >
          {{ status.next_action.label }}
          <span v-if="status.next_action.hint" class="cta-hint">{{ status.next_action.hint }}</span>
        </button>
      </div>
    </div>

    <div v-if="checklist.length" class="task-checklist">
      <button
        v-for="item in checklist"
        :key="item.key"
        type="button"
        class="task-row"
        :class="{ done: item.done, 'focus-flash': focusKey === item.key }"
        :id="`${item.key}-section`"
        @click="onTaskClick(item)"
      >
        <span class="task-icon">{{ item.done ? '✓' : '○' }}</span>
        <span class="task-label">{{ item.label }}</span>
        <span class="task-reward">{{ item.reward }}</span>
        <span v-if="item.key === 'signin' && !item.done && signing" class="task-loading">…</span>
      </button>
    </div>

    <div
      v-if="quiz && !quiz.answered"
      id="quiz-section"
      class="quiz-block glass-inner"
      :class="{ 'focus-flash': focusKey === 'quiz' }"
    >
      <div class="quiz-head">
        <strong>今日主队问答</strong>
        <span class="quiz-tag">+15 币</span>
      </div>
      <p class="quiz-q">{{ quiz.question }}</p>
      <div class="quiz-grid">
        <button
          v-for="(opt, idx) in quiz.options"
          :key="idx"
          type="button"
          class="quiz-opt"
          @click="emit('answer-quiz', Number(idx))"
        >
          {{ opt }}
        </button>
      </div>
    </div>
    <div
      v-else-if="quizLoadFailed || (status && !status.quiz?.answered && !quiz)"
      id="quiz-section"
      class="quiz-block glass-inner quiz-error"
      :class="{ 'focus-flash': focusKey === 'quiz' }"
    >
      <p>今日问答加载失败</p>
      <button type="button" class="quiz-retry" @click="emit('reload-quiz')">重新加载</button>
    </div>
    <div
      v-else-if="quiz && quiz.answered"
      id="quiz-section"
      class="quiz-block glass-inner answered"
    >
      <div class="quiz-head">
        <strong>今日主队问答</strong>
        <span class="quiz-tag" :class="quiz.was_correct ? 'ok' : 'fail'">
          {{ quiz.was_correct ? '已答对' : '已答错' }}
        </span>
      </div>
      <p class="quiz-q muted">{{ quiz.question }}</p>
    </div>

    <el-alert
      v-if="status?.match_day_message"
      type="success"
      :closable="true"
      show-icon
      class="task-alert"
      :title="status.match_day_message"
    />
    <el-alert
      v-if="status?.streak_risk"
      type="warning"
      :closable="true"
      class="task-alert"
      :title="status.streak_risk.message"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { DailyStatus } from '../../api/commerce'
import { navigateDailyAction } from '../../utils/dailyActionNav'
import { openOfficialQqGroupModal } from '../../composables/useOfficialQqGroup'

const props = defineProps<{
  status: DailyStatus | null
  quiz: Record<string, unknown> | null
  quizLoadFailed?: boolean
  focusKey?: string | null
  signing?: boolean
}>()

const emit = defineEmits<{
  signin: []
  'answer-quiz': [idx: number]
  'reload-quiz': []
}>()

const router = useRouter()
const route = useRoute()

const checklist = computed(() =>
  (props.status?.checklist ?? []).filter((c) => !c.optional),
)

function goNext() {
  navigateDailyAction(router, route, props.status?.next_action ?? null)
}

function onTaskClick(item: { key: string; done: boolean }) {
  if (item.key === 'signin' && !item.done) {
    emit('signin')
    return
  }
  if (item.key === 'qq_group' && !item.done) {
    openOfficialQqGroupModal()
    return
  }
  if (item.done && item.key !== 'quiz') return
  if (item.key === 'quiz' || item.key === 'signin' || item.key === 'pending') {
    navigateDailyAction(router, route, {
      key: item.key,
      path: `/me?tab=overview&focus=${item.key === 'pending' ? 'predictions' : item.key}`,
    })
    return
  }
  if (item.key === 'predict') router.push('/predict')
}
</script>

<style scoped>
.today-tasks {
  padding: 16px;
  margin-bottom: 12px;
}

.tasks-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 14px;
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
  font-size: 9px;
  font-weight: 600;
  color: var(--wc-text-muted);
  text-align: center;
  padding: 0 6px;
  line-height: 1.2;
}

.tasks-main {
  flex: 1;
  min-width: 0;
}

.tasks-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #f5f0e8;
  margin-bottom: 8px;
}

.streak-hint {
  font-weight: 500;
  color: var(--wc-text-muted);
  font-size: 0.82rem;
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

.main-cta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.45);
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.18), rgba(201, 120, 138, 0.1));
  color: #f5f0e8;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
}

.cta-hint {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--wc-text-muted);
}

.task-checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.25);
  background: rgba(12, 14, 28, 0.45);
  color: #f5f0e8;
  font-size: 0.85rem;
  cursor: pointer;
  text-align: left;
}

.task-row:not(.done):hover {
  border-color: rgba(212, 165, 116, 0.5);
  background: rgba(212, 165, 116, 0.08);
}

.task-row.done {
  opacity: 0.65;
  border-color: rgba(103, 194, 58, 0.3);
}

.task-icon {
  flex-shrink: 0;
  font-size: 0.9rem;
  color: var(--wc-accent-gold);
}

.task-label {
  flex: 1;
}

.task-reward {
  font-size: 0.75rem;
  color: var(--wc-accent-gold);
}

.task-loading {
  color: var(--wc-text-muted);
}

.quiz-block {
  padding: 14px;
  border-radius: 10px;
  margin-top: 4px;
}

.quiz-block.answered {
  opacity: 0.85;
}

.quiz-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.quiz-head strong {
  color: #f0d9b5;
  font-size: 0.9rem;
}

.quiz-tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(212, 165, 116, 0.18);
  color: var(--wc-accent-gold);
}

.quiz-tag.ok {
  background: rgba(103, 194, 58, 0.15);
  color: #8fd48a;
}

.quiz-tag.fail {
  background: rgba(245, 108, 108, 0.15);
  color: #f89898;
}

.quiz-q {
  margin: 0 0 12px;
  font-size: 0.9rem;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.9);
}

.quiz-q.muted {
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 0;
}

.quiz-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

@media (max-width: 520px) {
  .quiz-grid {
    grid-template-columns: 1fr;
  }
}

.quiz-opt {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  background: rgba(12, 14, 28, 0.6);
  color: #f5f0e8;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.quiz-opt:hover {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.12);
}

.quiz-error {
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
}

.quiz-retry {
  margin-top: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.4);
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
  cursor: pointer;
}

.task-alert {
  margin-top: 10px;
  margin-bottom: 0;
}

.focus-flash {
  animation: focusPulse 2s ease;
}

@keyframes focusPulse {
  0%, 100% { box-shadow: none; }
  20%, 60% { box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.7), 0 0 24px rgba(212, 165, 116, 0.35); }
}
</style>
