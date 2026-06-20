<template>
  <div class="pass-track">
    <section class="pass-hero glass-panel">
      <div class="hero-top">
        <div class="level-ring" :class="{ maxed: isMaxLevel }">
          <span class="level-num">{{ summary.level }}</span>
          <span class="level-sub">LV</span>
        </div>
        <div class="hero-meta">
          <h2 class="season-name">{{ summary.season.name }}</h2>
          <p v-if="seasonEnds" class="season-ends">赛季至 {{ seasonEnds }}</p>
          <div class="xp-bar">
            <div class="xp-fill" :style="{ width: `${xpPct}%` }" />
          </div>
          <p class="xp-label">
            {{ summary.xp }} XP
            <template v-if="summary.xp_to_next">
              · 距 Lv.{{ summary.next_level }} 还差 <strong>{{ summary.xp_to_next }}</strong>
            </template>
            <template v-else> · 已满级</template>
          </p>
        </div>
      </div>

      <div v-if="claimableCount" class="claimable-strip">
        <span class="claimable-dot" />
        <span>{{ claimableCount }} 项奖励可领取</span>
        <button type="button" class="jump-btn" @click="scrollToClaimable">查看</button>
        <button
          type="button"
          class="claim-all-btn"
          :disabled="!!claimingAll"
          @click="$emit('claim-all')"
        >
          {{ claimingAll ? '领取中…' : '一键领取' }}
        </button>
      </div>

      <div class="pass-actions">
        <el-tag v-if="summary.premium_unlocked" type="warning" effect="dark" size="small">尊享已解锁</el-tag>
        <template v-else>
          <el-button type="warning" size="small" @click="$emit('buy-premium')">
            解锁尊享 ¥{{ (summary.premium_price_fen / 100).toFixed(0) }}
          </el-button>
          <el-button
            v-if="summary.premium_plus_price_fen"
            plain
            size="small"
            type="warning"
            @click="$emit('buy-premium-plus')"
          >
            尊享+越级10级 ¥{{ (summary.premium_plus_price_fen / 100).toFixed(0) }}
          </el-button>
        </template>
        <el-button
          v-if="!summary.xp_boost_active"
          plain
          size="small"
          @click="$emit('buy-xp-boost')"
        >
          经验加成 · 30 币
        </el-button>
        <el-tag v-else type="success" size="small">XP +50% 生效中</el-tag>
      </div>
    </section>

    <div class="track-legend">
      <span><i class="dot free" /> 免费轨</span>
      <span><i class="dot premium" /> 尊享轨</span>
      <span class="legend-note">确定性奖励 · 非盲盒</span>
    </div>

    <div class="milestone-preview">
      <span class="mp-label">尊享限定卡里程碑</span>
      <div class="mp-cards">
        <div
          v-for="m in milestones"
          :key="m.level"
          class="mp-card"
          :class="{ reached: summary.level >= m.level, unlocked: summary.premium_unlocked }"
        >
          <span class="mp-lv">Lv.{{ m.level }}</span>
          <span class="mp-name">{{ m.label }}</span>
        </div>
      </div>
    </div>

    <div class="track-scroll">
      <div
        v-for="row in summary.tracks"
        :key="row.level"
        :ref="(el) => setRowRef(row.level, el)"
        class="track-row glass-inner"
        :class="rowClasses(row)"
      >
        <div class="lv-col">
          <span class="lv-num">Lv.{{ row.level }}</span>
          <span v-if="isPassMilestone(row.level)" class="milestone-tag">里程碑</span>
        </div>
        <div class="reward-col free">
          <p class="reward-label">免费</p>
          <RewardCell :reward="row.free" />
          <ClaimAction
            :claimable="row.free_claimable"
            :claimed="row.free_claimed"
            :loading="claiming === `${row.level}-free`"
            track="free"
            @claim="$emit('claim', row.level, 'free')"
          />
        </div>
        <div class="reward-col premium" :class="{ 'needs-premium': !summary.premium_unlocked }">
          <p class="reward-label">尊享</p>
          <RewardCell :reward="row.premium" premium />
          <ClaimAction
            :claimable="row.premium_claimable"
            :claimed="row.premium_claimed"
            :locked-premium="!summary.premium_unlocked"
            :loading="claiming === `${row.level}-premium`"
            track="premium"
            @claim="$emit('claim', row.level, 'premium')"
            @unlock="$emit('buy-premium')"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onMounted, type ComponentPublicInstance } from 'vue'
import type { CollectionPassSummary, PassReward, PassTrackLevel } from '@/api/collectionPass'
import { formatPassReward, formatSeasonEnds, isPassMilestone, PASS_MILESTONE_CARDS } from '@/utils/passRewardLabels'

const props = defineProps<{
  summary: CollectionPassSummary
  claiming?: string | null
  claimingAll?: boolean
}>()

defineEmits<{
  claim: [level: number, track: 'free' | 'premium']
  'claim-all': []
  'buy-premium': []
  'buy-premium-plus': []
  'buy-xp-boost': []
}>()

const rowRefs = new Map<number, HTMLElement>()

const milestones = PASS_MILESTONE_CARDS

const claimableCount = computed(() => props.summary.claimable_count ?? 0)
const seasonEnds = computed(() => formatSeasonEnds(props.summary.season.ends_at))
const isMaxLevel = computed(
  () => props.summary.level >= props.summary.season.max_level,
)

const xpPct = computed(() => {
  if (props.summary.xp_level_progress_pct != null) {
    return props.summary.xp_level_progress_pct
  }
  const lv = props.summary.level
  if (lv >= props.summary.season.max_level) return 100
  const cur = props.summary.tracks.find((t) => t.level === lv)
  const nxt = props.summary.tracks.find((t) => t.level === lv + 1)
  if (!cur || !nxt) return 100
  const span = nxt.threshold_xp - cur.threshold_xp
  if (span <= 0) return 100
  return Math.min(100, Math.round(((props.summary.xp - cur.threshold_xp) / span) * 100))
})

function setRowRef(level: number, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLElement) rowRefs.set(level, el)
  else rowRefs.delete(level)
}

function rowClasses(row: PassTrackLevel) {
  return {
    current: row.level === props.summary.level,
    milestone: isPassMilestone(row.level),
    'has-claimable': row.free_claimable || row.premium_claimable,
  }
}

function scrollToClaimable() {
  const target = props.summary.tracks.find((t) => t.free_claimable || t.premium_claimable)
  if (!target) return
  const el = rowRefs.get(target.level)
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

onMounted(() => {
  if (claimableCount.value) {
    void nextTick(() => scrollToClaimable())
  }
})

const RewardCell = defineComponent({
  props: {
    reward: { type: Object as () => PassReward, required: true },
    premium: { type: Boolean, default: false },
  },
  setup(p) {
    return () => {
      const { primary, secondary, isCard } = formatPassReward(p.reward)
      return h('div', { class: ['reward-cell', p.premium && 'is-premium', isCard && 'is-card'] }, [
        h('p', { class: 'reward-primary' }, primary),
        secondary ? h('p', { class: 'reward-secondary' }, secondary) : null,
      ])
    }
  },
})

const ClaimAction = defineComponent({
  props: {
    claimable: Boolean,
    claimed: Boolean,
    lockedPremium: Boolean,
    loading: Boolean,
    track: { type: String as () => 'free' | 'premium', required: true },
  },
  emits: ['claim', 'unlock'],
  setup(p, { emit }) {
    return () => {
      if (p.claimable) {
        return h(
          'button',
          {
            type: 'button',
            class: ['claim-btn', p.track],
            disabled: p.loading,
            onClick: () => emit('claim'),
          },
          p.loading ? '领取中…' : '领取',
        )
      }
      if (p.claimed) return h('span', { class: 'status claimed' }, '✓ 已领')
      if (p.lockedPremium) {
        return h(
          'button',
          { type: 'button', class: 'status unlock-link', onClick: () => emit('unlock') },
          '解锁尊享',
        )
      }
      return h('span', { class: 'status locked' }, '未达成')
    }
  },
})
</script>

<style scoped>
.pass-track {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pass-hero {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(212, 165, 116, 0.28);
  background: linear-gradient(145deg, rgba(212, 165, 116, 0.12), rgba(126, 184, 255, 0.06));
}

.hero-top {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.level-ring {
  flex-shrink: 0;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  border: 2px solid rgba(212, 165, 116, 0.55);
  box-shadow: 0 0 20px rgba(212, 165, 116, 0.15);
}

.level-ring.maxed {
  border-color: #7eb8ff;
  box-shadow: 0 0 20px rgba(126, 184, 255, 0.2);
}

.level-num {
  font-size: 1.35rem;
  font-weight: 800;
  line-height: 1;
  color: var(--wc-gold, #d4a574);
}

.level-sub {
  font-size: 0.58rem;
  letter-spacing: 0.12em;
  color: var(--wc-text-muted);
}

.hero-meta {
  flex: 1;
  min-width: 0;
}

.season-name {
  margin: 0 0 2px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #f5f0e8;
  line-height: 1.3;
}

.season-ends {
  margin: 0 0 8px;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.xp-bar {
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  margin-bottom: 6px;
}

.xp-fill {
  height: 100%;
  background: linear-gradient(90deg, #7eb8ff, #d4a574);
  border-radius: 999px;
  transition: width 0.4s ease;
}

.xp-label {
  margin: 0;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}

.xp-label strong {
  color: #7eb8ff;
}

.claimable-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 10px;
  background: rgba(61, 214, 140, 0.1);
  border: 1px solid rgba(61, 214, 140, 0.35);
  font-size: 0.8rem;
  color: #3dd68c;
}

.claimable-strip > span:nth-child(2) {
  flex: 1;
  min-width: 120px;
}

.claimable-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3dd68c;
  animation: pulse 1.5s ease infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.jump-btn {
  border: none;
  background: rgba(61, 214, 140, 0.2);
  color: #3dd68c;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.claim-all-btn {
  margin-left: auto;
  border: none;
  background: #3dd68c;
  color: #0e1020;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 5px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.claim-all-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.pass-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.track-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  padding: 0 4px;
}

.track-legend .dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.dot.free { background: #7eb8ff; }
.dot.premium { background: var(--wc-gold, #d4a574); }

.legend-note {
  margin-left: auto;
  opacity: 0.75;
}

.milestone-preview {
  padding: 10px 4px;
}

.mp-label {
  display: block;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  margin-bottom: 8px;
}

.mp-cards {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mp-card {
  flex: 1;
  min-width: 90px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  text-align: center;
  opacity: 0.55;
  transition: opacity 0.2s, border-color 0.2s;
}

.mp-card.reached.unlocked {
  opacity: 1;
  border-style: solid;
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.08);
}

.mp-card.reached:not(.unlocked) {
  opacity: 0.75;
  border-color: rgba(126, 184, 255, 0.25);
}

.mp-lv {
  display: block;
  font-size: 0.65rem;
  color: var(--wc-text-muted);
}

.mp-name {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--wc-gold);
  margin-top: 2px;
}

.track-scroll {
  max-height: min(52vh, 480px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 8px;
}

.track-row {
  display: grid;
  grid-template-columns: 48px 1fr 1fr;
  gap: 8px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid transparent;
  transition: border-color 0.2s, background 0.2s;
}

.track-row.current {
  border-color: rgba(126, 184, 255, 0.35);
  background: rgba(126, 184, 255, 0.06);
}

.track-row.milestone {
  border-color: rgba(212, 165, 116, 0.25);
}

.track-row.has-claimable {
  border-color: rgba(61, 214, 140, 0.4);
  box-shadow: 0 0 0 1px rgba(61, 214, 140, 0.12);
}

.lv-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 2px;
}

.lv-num {
  font-weight: 700;
  font-size: 0.82rem;
  color: var(--wc-gold);
}

.milestone-tag {
  font-size: 0.58rem;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(212, 165, 116, 0.2);
  color: var(--wc-gold);
  white-space: nowrap;
}

.reward-label {
  margin: 0 0 4px;
  font-size: 0.65rem;
  color: var(--wc-text-muted);
  letter-spacing: 0.06em;
}

.reward-col :deep(.reward-primary) {
  margin: 0 0 4px;
  font-size: 0.78rem;
  line-height: 1.35;
  color: #f5f0e8;
}

.reward-col :deep(.reward-secondary) {
  margin: 0 0 8px;
  font-size: 0.68rem;
  color: #7eb8ff;
}

.reward-col :deep(.is-card .reward-primary) {
  color: var(--wc-gold);
  font-weight: 600;
}

.reward-col.needs-premium {
  opacity: 0.72;
}

.reward-col :deep(.claim-btn) {
  border: none;
  border-radius: 8px;
  padding: 5px 12px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.reward-col :deep(.claim-btn.free) {
  background: rgba(126, 184, 255, 0.2);
  color: #7eb8ff;
}

.reward-col :deep(.claim-btn.premium) {
  background: rgba(212, 165, 116, 0.25);
  color: var(--wc-gold);
}

.reward-col :deep(.claim-btn:disabled) {
  opacity: 0.6;
  cursor: wait;
}

.reward-col :deep(.status) {
  font-size: 0.72rem;
}

.reward-col :deep(.status.claimed) {
  color: #3dd68c;
}

.reward-col :deep(.status.locked) {
  color: var(--wc-text-muted);
}

.reward-col :deep(.status.unlock-link) {
  border: none;
  background: transparent;
  color: var(--wc-gold);
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  font-size: 0.72rem;
}

@media (max-width: 420px) {
  .track-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .lv-col {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .legend-note {
    width: 100%;
    margin-left: 0;
  }
}
</style>
