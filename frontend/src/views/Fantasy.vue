<template>
  <div class="fantasy-page">
    <div class="page-header">
      <h1>数字阵容</h1>
      <p class="subtitle">用持有的球员卡组建阵容，按真实比赛表现每周积分 · 周一自动发放周榜球迷币</p>
    </div>

    <div v-if="loading" class="loading">
      <el-skeleton :rows="5" animated />
    </div>
    <template v-else>
      <div class="lineup-board glass-inner">
        <div class="board-head">
          <div>
            <span class="period">{{ lineup?.period_key }}</span>
            <span class="score">本周得分 <b>{{ lineup?.score ?? 0 }}</b></span>
            <span class="my-rank">
              {{ myRankLabel }}
            </span>
          </div>
        </div>
        <div class="reward-tiers">
          <span v-for="t in rewardTiers" :key="t.rank" class="tier-chip">第{{ t.rank }}名 {{ t.coins }}币</span>
        </div>
        <div class="slots">
          <div
            v-for="i in (lineup?.size || 5)"
            :key="i"
            class="slot"
            :class="{ filled: !!selected[i - 1] }"
            @click="onSlotClick(i - 1)"
          >
            <template v-if="slotCard(i - 1)">
              <div class="slot-img" :style="slotCard(i - 1)?.image_url ? { backgroundImage: `url(${slotCard(i - 1)?.image_url})` } : {}" />
              <span v-if="slotCard(i - 1)?.star && slotCard(i - 1)!.star > 1" class="slot-star">★{{ slotCard(i - 1)?.star }}</span>
              <span class="slot-name">{{ slotCard(i - 1)?.name }}</span>
            </template>
            <div v-else class="slot-empty">＋</div>
          </div>
        </div>
        <el-button type="primary" :loading="saving" :disabled="!dirty" @click="save">保存阵容</el-button>
      </div>

      <div v-if="scoreLogs.length" class="score-timeline glass-inner">
        <h3>本周计分</h3>
        <ul>
          <li v-for="(log, idx) in scoreLogs" :key="idx">
            <span class="st-match">{{ log.match_label || `比赛 #${log.match_id}` }}</span>
            <span class="st-pts">+{{ log.points }}</span>
            <span class="st-detail">{{ formatDetail(log.detail) }}</span>
          </li>
        </ul>
      </div>

      <div class="picker glass-inner">
        <div class="picker-head">
          <h3>我的球员卡</h3>
          <div class="filters">
            <el-select v-model="filterRarity" placeholder="稀有度" clearable size="small">
              <el-option label="普通" value="common" />
              <el-option label="稀有" value="rare" />
              <el-option label="史诗" value="epic" />
              <el-option label="传奇" value="legend" />
            </el-select>
            <el-select v-model="filterPosition" placeholder="位置" clearable size="small">
              <el-option v-for="p in positions" :key="p" :label="p" :value="p" />
            </el-select>
          </div>
        </div>
        <div v-if="!eligible.length" class="empty">
          暂无球员卡，<router-link to="/collection">去收藏册</router-link> / <router-link to="/market">交易行</router-link> / <router-link to="/mint">打新</router-link> 获取
        </div>
        <div v-else-if="!filteredEligible.length" class="empty">无符合筛选的球员卡</div>
        <div v-else class="picker-grid">
          <div
            v-for="card in filteredEligible"
            :key="card.user_card_id"
            v-memo="[card.user_card_id, isPicked(card.user_card_id), filterRarity, filterPosition]"
            class="pick-card"
            :class="[card.rarity, { picked: isPicked(card.user_card_id) }]"
            @click="addCard(card)"
          >
            <div class="pick-img" :style="card.image_url ? { backgroundImage: `url(${card.image_url})` } : {}">
              <span v-if="card.position" class="pos">{{ card.position }}</span>
              <span v-if="card.star > 1" class="star-badge">★{{ card.star }}</span>
            </div>
            <span class="pick-name">{{ card.name }}</span>
            <span v-if="card.rating" class="rating">{{ card.rating }}</span>
          </div>
        </div>
      </div>

      <div class="leaderboard glass-inner">
        <h3>本周阵容榜</h3>
        <div v-if="!leaderboard.length" class="empty">暂无排名，保存阵容后参与本周榜</div>
        <ol v-else>
          <li v-for="row in leaderboard" :key="row.rank">
            <span class="lb-rank" :class="{ top: row.rank <= 3 }">{{ row.rank }}</span>
            <span class="lb-name">{{ row.nickname }}</span>
            <span class="lb-score">{{ row.score }}</span>
          </li>
        </ol>
      </div>

      <p class="disclaimer">计分：进球/助攻/出场（球队参赛）× 星级系数；奖励为球迷币，无现金价值。</p>
    </template>

    <el-dialog v-model="slotDialog" title="槽位操作" width="min(320px, 92vw)" align-center append-to-body>
      <p v-if="activeSlotCard">{{ activeSlotCard.name }} · ★{{ activeSlotCard.star || 1 }}</p>
      <template #footer>
        <el-button @click="slotDialog = false">取消</el-button>
        <el-button type="danger" plain @click="confirmRemoveSlot">移出阵容</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getFantasy,
  saveFantasy,
  getFantasyLeaderboard,
  type FantasyEligibleCard,
  type FantasyLineup,
  type FantasyScoreLogItem,
} from '@/api/asset'
import { extractApiError } from '@/utils/apiError'
import { usePageMeta } from '@/composables/usePageMeta'

usePageMeta({
  title: '数字阵容 — 最后一舞',
  description: '用球员卡组建阵容，按真实比赛表现每周积分。',
  path: '/fantasy',
  noIndex: true,
})

const loading = ref(false)
const saving = ref(false)
const lineup = ref<FantasyLineup | null>(null)
const eligible = ref<FantasyEligibleCard[]>([])
const scoreLogs = ref<FantasyScoreLogItem[]>([])
const leaderboard = ref<{ rank: number; nickname: string; score: number }[]>([])
const myRank = ref<{ rank: number | null; score: number; on_board: boolean } | null>(null)
const rewardTiers = ref<{ rank: number; coins: number }[]>([])
const selected = ref<(FantasyEligibleCard | null)[]>([])
const dirty = ref(false)
const filterRarity = ref('')
const filterPosition = ref('')
const slotDialog = ref(false)
const activeSlotIndex = ref(-1)
let pollTimer: ReturnType<typeof setInterval> | null = null

const positions = computed(() => {
  const set = new Set<string>()
  eligible.value.forEach((c) => {
    if (c.position) set.add(c.position)
  })
  return [...set]
})

const filteredEligible = computed(() => {
  return eligible.value.filter((c) => {
    if (filterRarity.value && c.rarity !== filterRarity.value) return false
    if (filterPosition.value && c.position !== filterPosition.value) return false
    return true
  })
})

const myRankLabel = computed(() => {
  const r = myRank.value ?? lineup.value?.my_rank
  if (!r) return ''
  if (!r.on_board || r.rank == null) return '· 未上榜'
  return `· 第 ${r.rank} 名`
})

const activeSlotCard = computed(() => {
  if (activeSlotIndex.value < 0) return null
  return selected.value[activeSlotIndex.value]
})

function slotCard(i: number) {
  return selected.value[i] || null
}
function isPicked(id: number) {
  return selected.value.some((c) => c?.user_card_id === id)
}

function formatDetail(detail: Record<string, unknown>): string {
  const players = detail.players as Record<string, Record<string, number>> | undefined
  if (!players) return ''
  return Object.entries(players)
    .map(([name, p]) => {
      const parts: string[] = []
      if (p.goals) parts.push(`${p.goals}球`)
      if (p.assists) parts.push(`${p.assists}助`)
      if (p.appearance) parts.push('出场')
      return `${name} ${parts.join('/')}`
    })
    .join(' · ')
}

function addCard(card: FantasyEligibleCard) {
  if (isPicked(card.user_card_id)) {
    const idx = selected.value.findIndex((c) => c?.user_card_id === card.user_card_id)
    if (idx >= 0) removeSlot(idx)
    return
  }
  const size = lineup.value?.size || 5
  const empty = selected.value.findIndex((c) => !c)
  if (empty >= 0) {
    selected.value[empty] = card
  } else if (selected.value.length < size) {
    selected.value.push(card)
  } else {
    ElMessage.warning('阵容已满，点击槽位移出后再添加')
    return
  }
  dirty.value = true
}

function removeSlot(i: number) {
  selected.value[i] = null
  dirty.value = true
}

function onSlotClick(i: number) {
  if (!selected.value[i]) return
  activeSlotIndex.value = i
  slotDialog.value = true
}

function confirmRemoveSlot() {
  if (activeSlotIndex.value >= 0) removeSlot(activeSlotIndex.value)
  slotDialog.value = false
  activeSlotIndex.value = -1
}

async function save() {
  const ids = selected.value.filter(Boolean).map((c) => (c as FantasyEligibleCard).user_card_id)
  if (!ids.length) {
    ElMessage.warning('请至少选择 1 张球员卡')
    return
  }
  saving.value = true
  try {
    lineup.value = await saveFantasy(ids)
    dirty.value = false
    ElMessage.success('阵容已保存')
    await refreshScores()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function refreshScores() {
  try {
    const [res, lbRes] = await Promise.all([getFantasy(), getFantasyLeaderboard()])
    lineup.value = res.lineup
    scoreLogs.value = res.score_logs || []
    myRank.value = lbRes.my_rank ?? res.lineup.my_rank ?? null
    rewardTiers.value = lbRes.reward_tiers ?? res.lineup.reward_tiers ?? []
    leaderboard.value = lbRes.items
  } catch {
    /* ignore poll errors */
  }
}

async function load() {
  loading.value = true
  try {
    const [res, lbRes] = await Promise.all([getFantasy(), getFantasyLeaderboard()])
    lineup.value = res.lineup
    eligible.value = res.eligible
    scoreLogs.value = res.score_logs || []
    leaderboard.value = lbRes.items
    myRank.value = lbRes.my_rank ?? res.lineup.my_rank ?? null
    rewardTiers.value = lbRes.reward_tiers ?? res.lineup.reward_tiers ?? []
    const size = res.lineup.size
    const slots: (FantasyEligibleCard | null)[] = new Array(size).fill(null)
    res.lineup.slots.forEach((s, i) => {
      if (i < size) {
        slots[i] = {
          user_card_id: s.user_card_id,
          card_code: '',
          name: s.name,
          rarity: s.rarity,
          image_url: s.image_url,
          star: s.star,
        }
      }
    })
    selected.value = slots
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
  pollTimer = setInterval(() => void refreshScores(), 60000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.fantasy-page {
  max-width: 760px;
  margin: 0 auto;
  padding-bottom: calc(var(--wc-bottom-nav-height, 56px) + 24px);
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 1.5rem;
  color: var(--wc-accent-gold);
}
.subtitle {
  margin: 0 0 16px;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.glass-inner {
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 16px;
}
.board-head {
  margin-bottom: 8px;
}
.period {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  margin-right: 10px;
}
.score b {
  color: var(--wc-accent-gold);
  font-size: 1.1rem;
}
.my-rank {
  font-size: 0.75rem;
  color: #6eb5e0;
}
.reward-tiers {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.tier-chip {
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(212, 165, 116, 0.12);
  color: #f0b86c;
}
.slots {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.slot {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: 10px;
  border: 1px dashed rgba(212, 165, 116, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: pointer;
}
.slot.filled {
  border-style: solid;
}
.slot-img {
  position: absolute;
  inset: 0;
  background: linear-gradient(160deg, rgba(40, 30, 20, 0.6), rgba(20, 16, 30, 0.9));
  background-size: cover;
  background-position: center;
}
.slot-star {
  position: absolute;
  top: 4px;
  left: 4px;
  font-size: 0.55rem;
  color: #f0b86c;
}
.slot-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  font-size: 0.6rem;
  padding: 3px 4px;
  background: rgba(0, 0, 0, 0.6);
  color: #f0d9b5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.slot-empty {
  font-size: 1.4rem;
  color: rgba(212, 165, 116, 0.5);
}
.score-timeline h3 {
  margin: 0 0 10px;
  font-size: 0.9rem;
}
.score-timeline ul {
  margin: 0;
  padding: 0;
  list-style: none;
}
.score-timeline li {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.78rem;
}
.st-match {
  color: var(--wc-text-secondary);
  flex: 1;
  min-width: 120px;
}
.st-pts {
  color: var(--wc-accent-gold);
  font-weight: 700;
}
.st-detail {
  width: 100%;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.picker-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.picker-head h3 {
  margin: 0;
  font-size: 0.95rem;
}
.filters {
  display: flex;
  gap: 8px;
}
.picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
}
.pick-card {
  position: relative;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid transparent;
}
.pick-card.picked {
  border-color: var(--wc-accent-gold);
}
.pick-img {
  aspect-ratio: 3 / 4;
  background: linear-gradient(160deg, rgba(40, 30, 20, 0.6), rgba(20, 16, 30, 0.9));
  background-size: cover;
  background-position: center;
  position: relative;
}
.pos {
  position: absolute;
  top: 4px;
  left: 4px;
  font-size: 0.55rem;
  padding: 1px 5px;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.6);
  color: #e8c88a;
}
.star-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  font-size: 0.55rem;
  color: #f0b86c;
}
.rating {
  position: absolute;
  top: 4px;
  right: 4px;
  font-size: 0.62rem;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.6);
  color: #5fc88f;
}
.pick-name {
  display: block;
  font-size: 0.6rem;
  padding: 3px 4px;
  background: rgba(0, 0, 0, 0.5);
  color: #f0d9b5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.empty {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  padding: 12px 0;
}
.empty a {
  color: var(--wc-accent-gold);
}
.leaderboard h3 {
  margin: 0 0 12px;
  font-size: 0.95rem;
}
.leaderboard ol {
  margin: 0;
  padding: 0;
  list-style: none;
}
.leaderboard li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.lb-rank {
  width: 22px;
  text-align: center;
  font-weight: 700;
  color: var(--wc-text-muted);
}
.lb-rank.top {
  color: var(--wc-accent-gold);
}
.lb-name {
  flex: 1;
  font-size: 0.85rem;
}
.lb-score {
  font-weight: 700;
  color: var(--wc-accent-gold);
}
.disclaimer {
  margin-top: 10px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  text-align: center;
}
@media (max-width: 520px) {
  .slots {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
