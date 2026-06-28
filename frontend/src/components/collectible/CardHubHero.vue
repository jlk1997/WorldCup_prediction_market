<template>
  <section v-if="isLoggedIn" class="card-hub-hero glass-panel">
    <div class="hub-head">
      <div>
        <h2 class="hub-title">卡牌中心</h2>
        <p class="hub-sub">获卡 · 对决上分 · 文昌链凭证</p>
      </div>
      <router-link to="/leaderboard?board=duel_elo" class="hub-rank-link">排位榜</router-link>
    </div>

    <p v-if="seasonLine" class="hub-season">{{ seasonLine }}</p>

    <DuelStatsBar class="hub-stats" />

    <div class="hub-drop glass-inner" v-if="dropHint">
      <span class="drop-icon">🃏</span>
      <div class="drop-text">
        <strong>{{ dropHint.label }}</strong>
        <span v-if="dropHint.sub">{{ dropHint.sub }}</span>
      </div>
      <router-link :to="dropHint.path" class="drop-go">{{ dropHint.cta }}</router-link>
    </div>

    <div class="hub-actions">
      <button
        type="button"
        class="hub-match-btn"
        :disabled="matchBusy || matchInQueue"
        @click="startQuickMatch"
      >
        <span v-if="matchInQueue">匹配中… {{ matchWaitSec }}s</span>
        <span v-else-if="matchBusy">组牌中…</span>
        <span v-else>⚔️ 快速匹配对决</span>
      </button>
      <router-link to="/arena#duel" class="hub-secondary">
        擂台组牌
        <span v-if="pendingCount" class="pending-badge">{{ pendingCount }}</span>
      </router-link>
    </div>

    <p v-if="matchNotice" class="hub-notice">{{ matchNotice }}</p>
    <p v-if="matchError" class="hub-error">{{ matchError }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DuelStatsBar from '@/components/asset/DuelStatsBar.vue'
import { isLoggedIn } from '@/stores/authStore'
import { getCollectibleSummary, type CollectibleSummary } from '@/api/collectible'
import {
  enterDuelMatch,
  cancelDuelMatch,
  getDuelMatchStatus,
  getDuelPending,
  recommendDuelDeck,
  getDuelSeasonMe,
} from '@/api/asset'
import { trackEvent } from '@/utils/analytics'
import { useAssetRealname } from '@/composables/useAssetRealname'

const router = useRouter()
const { ensureVerified } = useAssetRealname()

const summary = ref<CollectibleSummary | null>(null)
const pendingCount = ref(0)
const matchBusy = ref(false)
const matchInQueue = ref(false)
const matchWaitSec = ref(0)
const matchNotice = ref('')
const matchError = ref('')
const seasonLine = ref('')

let pollTimer: ReturnType<typeof setInterval> | null = null
let waitTimer: ReturnType<typeof setInterval> | null = null

const dropHint = computed(() => {
  const s = summary.value
  if (!s) return null
  if (s.owned_count === 0) {
    return {
      label: '首张球星卡：猜中比赛必掉',
      sub: '主队卡牌加权 · 约 30 秒完成首猜',
      path: '/predict',
      cta: '去竞猜',
    }
  }
  if (s.next_signin_milestone) {
    return {
      label: s.next_signin_milestone.label,
      sub: '签到里程碑限定掉落',
      path: '/me',
      cta: '去签到',
    }
  }
  return {
    label: '猜中掉卡 · 对决胜利也有机会得卡',
    sub: `已收集 ${s.owned_count} 张 · 完成度 ${s.completion_pct}%`,
    path: '/predict',
    cta: '去获卡',
  }
})

function clearTimers() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (waitTimer) {
    clearInterval(waitTimer)
    waitTimer = null
  }
}

async function pollMatchStatus() {
  try {
    const st = await getDuelMatchStatus()
    matchInQueue.value = st.in_queue === true
    if (st.matched && st.duel_id) {
      clearTimers()
      matchInQueue.value = false
      router.push(`/arena/battle/${st.duel_id}`)
    }
  } catch {
    /* ignore */
  }
}

function startWaitTimer() {
  matchWaitSec.value = 0
  if (waitTimer) clearInterval(waitTimer)
  waitTimer = setInterval(() => {
    matchWaitSec.value += 1
  }, 1000)
}

async function startQuickMatch() {
  if (!(await ensureVerified('卡牌对决'))) return
  matchBusy.value = true
  matchError.value = ''
  matchNotice.value = ''
  try {
    const rec = await recommendDuelDeck()
    if (!rec.card_ids?.length || rec.card_ids.length < 3) {
      matchError.value = '可用出战卡不足，请先获得或拆分叠卡'
      router.push('/collection?tab=album')
      return
    }
    const res = await enterDuelMatch(rec.card_ids.slice(0, 3), 0)
    trackEvent('duel_match_enter', { source: 'card_hub', match_mode: 'casual' })
    matchInQueue.value = true
    matchNotice.value = res.notice || '已进入匹配队列'
    startWaitTimer()
    clearTimers()
    pollTimer = setInterval(() => void pollMatchStatus(), 2500)
    void pollMatchStatus()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    matchError.value = typeof msg === 'string' ? msg : '无法进入匹配，请前往擂台手动组牌'
  } finally {
    matchBusy.value = false
  }
}

async function loadMeta() {
  if (!isLoggedIn.value) return
  try {
    summary.value = await getCollectibleSummary()
    const pending = await getDuelPending()
    pendingCount.value = pending.length
    const season = await getDuelSeasonMe().catch(() => null)
    if (season?.name) {
      seasonLine.value = `${season.name} · ${season.tier?.label || '青铜'} · 剩余 ${season.days_left ?? 0} 天`
    } else {
      seasonLine.value = ''
    }
  } catch {
    summary.value = null
  }
}

function onDuelMatched(ev: Event) {
  const duelId = (ev as CustomEvent).detail?.duel_id
  if (duelId) {
    clearTimers()
    matchInQueue.value = false
    router.push(`/arena/battle/${duelId}`)
  }
}

onMounted(async () => {
  await loadMeta()
  const st = await getDuelMatchStatus().catch(() => null)
  if (st?.in_queue) {
    matchInQueue.value = true
    startWaitTimer()
    pollTimer = setInterval(() => void pollMatchStatus(), 2500)
  }
  window.addEventListener('duel-matched', onDuelMatched as EventListener)
})

onUnmounted(() => {
  clearTimers()
  window.removeEventListener('duel-matched', onDuelMatched as EventListener)
  if (matchInQueue.value) {
    void cancelDuelMatch().catch(() => {})
  }
})

defineExpose({ refresh: loadMeta })
</script>

<style scoped>
.card-hub-hero {
  margin: 12px 0;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(212, 165, 116, 0.28);
}
.hub-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}
.hub-title {
  margin: 0;
  font-size: 1.05rem;
  color: var(--wc-accent-gold);
}
.hub-sub {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.hub-rank-link {
  font-size: 0.72rem;
  color: #7eb8ff;
  text-decoration: none;
  white-space: nowrap;
}
.hub-season {
  margin: 0 0 10px;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.hub-stats {
  margin-bottom: 10px;
}
.hub-drop {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  margin-bottom: 12px;
}
.drop-icon {
  font-size: 1.2rem;
}
.drop-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.drop-text strong {
  font-size: 0.82rem;
  color: var(--wc-text-secondary);
}
.drop-text span {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.drop-go {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--wc-accent-gold);
  text-decoration: none;
}
.hub-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.hub-match-btn {
  flex: 1;
  min-width: 140px;
  min-height: 44px;
  border: none;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 800;
  color: #1a1208;
  cursor: pointer;
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
}
.hub-match-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.hub-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.78rem;
  font-weight: 600;
  text-decoration: none;
  color: var(--wc-text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
}
.pending-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #e85d5d;
  color: #fff;
  font-size: 0.62rem;
  line-height: 18px;
  text-align: center;
}
.hub-notice {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: #7eb8ff;
}
.hub-error {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: #f89898;
}
</style>
