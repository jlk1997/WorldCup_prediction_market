<template>
  <Teleport to="body">
    <div v-if="visible" class="duel-coach-root">
      <div class="coach-backdrop" @click.self="dismiss" />
      <div class="coach-tooltip glass-panel">
        <p class="coach-step">卡牌对决</p>
        <h3>用球星卡快速匹配</h3>
        <p>在卡牌中心组 3 张出战卡，快速匹配对决 · 胜利有机会掉卡 · ELO 冲榜</p>
        <div class="coach-actions">
          <el-button text @click="dismiss">稍后</el-button>
          <el-button type="primary" @click="goDuel">去对决</el-button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { trackEvent } from '@/utils/analytics'
import {
  GuidePriority,
  flushGuideQueue,
  isGuideBlocked,
  notifyGuideClosed,
  notifyGuideOpened,
  registerGuide,
  requestGuide,
  unregisterGuide,
} from '@/composables/useGuideOrchestrator'
import { guideModalState, isFeatureTourPending } from '@/composables/useGuideModal'

const STORAGE_KEY = 'wc_first_duel_coach'
const COACH_ID = 'first-duel-coach'

const visible = ref(false)
const router = useRouter()

function dismiss() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, '1')
  notifyGuideClosed(COACH_ID)
  flushGuideQueue()
}

function goDuel() {
  trackEvent('duel_coach_cta', { path: '/collection' })
  dismiss()
  router.push('/collection')
}

function tryOpen() {
  if (localStorage.getItem(STORAGE_KEY)) return
  if (isFeatureTourPending()) return
  if (guideModalState.open) return
  if (isGuideBlocked(GuidePriority.FirstDuelCoach)) return
  visible.value = true
  notifyGuideOpened(COACH_ID, GuidePriority.FirstDuelCoach)
  trackEvent('duel_coach_show')
}

onMounted(() => {
  registerGuide(COACH_ID, {
    priority: GuidePriority.FirstDuelCoach,
    isActive: () => visible.value,
    open: () => tryOpen(),
  })
  requestGuide(COACH_ID)
})

onUnmounted(() => {
  unregisterGuide(COACH_ID)
  if (visible.value) notifyGuideClosed(COACH_ID)
})
</script>

<style scoped>
.duel-coach-root {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.coach-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
}
.coach-tooltip {
  position: relative;
  max-width: 360px;
  padding: 18px 20px;
  border-radius: 14px;
  z-index: 1;
}
.coach-step {
  margin: 0 0 6px;
  font-size: 0.72rem;
  color: var(--wc-accent-gold);
}
h3 {
  margin: 0 0 8px;
  font-size: 1.05rem;
}
p {
  margin: 0 0 14px;
  font-size: 0.82rem;
  color: var(--wc-text-secondary);
  line-height: 1.5;
}
.coach-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
