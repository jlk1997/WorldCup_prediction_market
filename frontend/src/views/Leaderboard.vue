<template>
  <div class="leaderboard page-shell mobile-page">
    <div class="header glass-panel">
      <h1>球迷排行榜</h1>
      <p>竞猜积分 · 军团贡献 · 猜中率 — 纯娱乐数值排行</p>

      <InvitePromptBar v-if="authState.accessToken" scene="leaderboard" />

      <div
        v-if="showSeasonRewards && rewardTiers?.tiers?.length"
        class="season-rewards glass-inner"
      >
        <div class="season-rewards-head">
          <span class="trophy" aria-hidden="true">🏆</span>
          <div>
            <strong>赛季总榜 · 赛后虚拟奖励</strong>
            <p>上榜用户赛后发放球迷币 / 积分 / 装扮额度（不可提现）</p>
          </div>
        </div>
        <div class="tier-grid">
          <div v-for="t in rewardTierPreview" :key="t.rank" class="tier-chip">
            <span class="tier-rank">第 {{ t.rank }} 名</span>
            <span class="tier-reward">
              {{ t.coins }} 币
              <template v-if="t.redeem_points"> · {{ t.redeem_points }} 可用积分</template>
            </span>
          </div>
        </div>
        <p class="tier-more">第 4–10 名亦有档位 · 详见冲榜弹窗说明</p>
      </div>

      <div v-if="mySummary" class="my-summary glass-inner">
        <div class="my-title">我的排名</div>
        <div class="my-grid">
          <div class="my-stat">
            <span class="label">累计积分</span>
            <strong>{{ mySummary.season_points }}</strong>
            <span class="rank-tag">第 {{ mySummary.season_rank ?? '—' }} 名</span>
          </div>
          <div class="my-stat">
            <span class="label">可用积分</span>
            <strong>{{ mySummary.redeem_points }}</strong>
            <span class="rank-tag">第 {{ mySummary.redeem_rank ?? '—' }} 名</span>
          </div>
          <div class="my-stat">
            <span class="label">今日累计</span>
            <strong>{{ mySummary.daily_points }}</strong>
            <span class="rank-tag">{{ mySummary.daily_rank ? `第 ${mySummary.daily_rank} 名` : '今日暂无' }}</span>
          </div>
          <div class="my-stat">
            <span class="label">军团贡献</span>
            <strong>{{ mySummary.battalion_points }}</strong>
            <span class="rank-tag">
              {{ mySummary.battalion_team ? `${mySummary.battalion_team} 第 ${mySummary.battalion_rank ?? '—'} 名` : '未选主队' }}
            </span>
          </div>
          <div class="my-stat">
            <span class="label">竞猜准度</span>
            <strong>{{ mySummary.predict.win_rate }}%</strong>
            <span class="rank-tag">
              {{ mySummary.predict.settled }} 场 ·
              {{ mySummary.predict_accuracy_rank ? `准度榜第 ${mySummary.predict_accuracy_rank} 名` : '满5场上榜' }}
            </span>
          </div>
          <div v-if="mySummary.duel_elo != null" class="my-stat">
            <span class="label">对决 ELO</span>
            <strong>{{ mySummary.duel_elo }}</strong>
            <span class="rank-tag">
              {{ mySummary.duel_elo_tier?.label || '青铜' }} · 第 {{ mySummary.duel_elo_rank ?? '—' }} 名
            </span>
          </div>
        </div>
        <p v-if="mySummary.win_streak >= 2" class="streak-hint">当前 {{ mySummary.win_streak }} 连胜 · 猜中可额外加分</p>
        <p v-if="mySummary.season_gap_to_prev" class="gap-hint">
          累计积分再 +{{ mySummary.season_gap_to_prev }} 分即可超过上一名
        </p>
        <p v-if="mySummary.redeem_gap_to_prev" class="gap-hint">
          可用积分再 +{{ mySummary.redeem_gap_to_prev }} 分即可超过上一名
        </p>
        <div v-if="mySummary.season_gap_to_prev || mySummary.redeem_gap_to_prev" class="gap-cta-row">
          <el-button type="primary" size="small" @click="$router.push('/predict')">去竞猜赚积分</el-button>
          <el-button plain size="small" @click="openShareSheet">邀友一起冲榜</el-button>
        </div>
      </div>

      <div class="board-tabs mobile-segment">
        <el-radio-group v-model="board" @change="onBoardChange">
        <el-radio-button value="points">累计积分榜</el-radio-button>
        <el-radio-button value="redeem_points">可用积分榜</el-radio-button>
        <el-radio-button value="predict_accuracy">竞猜准度</el-radio-button>
        <el-radio-button value="battalion">军团榜</el-radio-button>
        <el-radio-button value="supporter">应援榜</el-radio-button>
        <el-radio-button value="star_heat">球星热力</el-radio-button>
        <el-radio-button value="star_accuracy">球星准度</el-radio-button>
        <el-radio-button value="contribution">主队贡献</el-radio-button>
        <el-radio-button value="referral">召友榜</el-radio-button>
        <el-radio-button value="duel_elo">对决 ELO</el-radio-button>
        <el-radio-button value="duel_wins">对决胜场</el-radio-button>
        <el-radio-button value="fans">粉丝榜</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="board === 'points' || board === 'redeem_points' || board === 'battalion' || board === 'supporter'" class="board-tabs mobile-segment">
        <el-radio-group
          v-model="period"
          @change="load"
          class="period"
        >
        <el-radio-button value="daily">日榜</el-radio-button>
        <el-radio-button value="weekly">周榜</el-radio-button>
        <el-radio-button value="season">赛季总榜</el-radio-button>
        </el-radio-group>
      </div>

      <el-alert v-if="board === 'referral' && referralCountdown" type="warning" :closable="false" class="ref-countdown">
        {{ referralCountdown }}
      </el-alert>

      <el-alert v-if="board === 'referral' && referralMyRank" type="success" :closable="false" class="my-ref-hint">
        你本周召友榜排名第 {{ referralMyRank }} 名 · 有效邀请 {{ referralMyScore }} 人
      </el-alert>

      <div v-if="board === 'referral' && isLoggedIn" class="referral-cta-row">
        <el-button type="primary" @click="openShareSheet">邀请好友冲榜</el-button>
        <el-button plain @click="$router.push('/invite')">召友中心</el-button>
      </div>

      <div v-if="board === 'supporter'" class="supporter-team-pick">
        <el-select v-model="supporterTeamId" size="small" placeholder="选择球队" @change="load">
          <el-option v-for="t in teamOptions" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </div>

      <el-alert v-if="board === 'duel_elo' || board === 'duel_wins'" type="info" :closable="false" class="rule-hint">
        三局两胜卡牌对决 ·
        <router-link to="/arena#duel">去擂台组牌开战</router-link>
      </el-alert>

      <el-alert v-if="boardDescription" :title="boardDescription" type="info" show-icon :closable="false" class="rule-hint" />
    </div>

    <div class="boards">
      <div class="board glass-panel" v-loading="loading">
        <h2>{{ boardTitle }}<span v-if="periodLabel" class="period-label"> · {{ periodLabel }}</span></h2>

        <template v-if="board === 'points' || board === 'redeem_points' || board === 'predict_accuracy' || board === 'battalion' || board === 'supporter' || board === 'duel_elo' || board === 'duel_wins'">
          <div
            v-for="row in unifiedRows"
            :key="row.user_id"
            class="row"
            :class="{ me: row.is_me }"
          >
            <span class="rank" :class="{ top: (row.rank ?? 0) <= 3 }">{{ row.rank }}</span>
            <span class="tier" v-if="row.tier_label">{{ row.tier_label }}</span>
            <span class="name">{{ row.nickname }}<span v-if="row.is_me" class="me-tag">我</span></span>
            <span class="pts">{{ formatPoints(row) }}</span>
            <span class="streak" v-if="row.win_streak >= 3">🔥{{ row.win_streak }}</span>
            <span class="streak mild" v-else-if="row.win_streak">🔥{{ row.win_streak }}</span>
          </div>
          <el-empty v-if="!loading && !unifiedRows.length" description="暂无数据" />
        </template>

        <template v-else-if="board === 'star_heat'">
          <div v-for="(row, idx) in starRows" :key="row.player_id" class="row">
            <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
            <span class="name">{{ row.player_name }}</span>
            <span class="pts">{{ row.global_heat ?? 0 }} 热力</span>
          </div>
          <el-empty v-if="!loading && !starRows.length" description="暂无球星热力" />
        </template>

        <template v-else-if="board === 'star_accuracy'">
          <div v-for="(row, idx) in accuracyRows" :key="row.player_id" class="acc-block">
            <div class="row">
              <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
              <span class="name">{{ row.player_name }}</span>
              <span class="pts">{{ row.accuracy_pct }}%</span>
              <span class="sample">n={{ row.sample_size }}</span>
            </div>
            <div class="top-fans" v-if="row.top_fans?.length">
              <span v-for="f in row.top_fans.slice(0, 3)" :key="f.user_id" class="fan-chip">
                {{ f.nickname }} {{ f.wins }}胜
              </span>
            </div>
          </div>
          <el-empty v-if="!loading && !accuracyRows.length" description="样本不足，暂无准度榜" />
        </template>

        <template v-else-if="board === 'referral'">
          <div
            v-for="row in referralRows"
            :key="row.user_id"
            class="row"
            :class="{ me: row.user_id === authState.user?.id }"
          >
            <span class="rank" :class="{ top: row.rank <= 3 }">{{ row.rank }}</span>
            <span class="name">{{ row.nickname }}<span v-if="row.user_id === authState.user?.id" class="me-tag">我</span></span>
            <span class="pts">{{ row.score }} 人</span>
          </div>
          <el-empty v-if="!loading && !referralRows.length" description="本周暂无有效邀请" />
        </template>

        <template v-else-if="board === 'contribution'">
          <div v-for="(row, idx) in contribution" :key="row.user_id" class="row" :class="{ me: row.user_id === authState.user?.id }">
            <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
            <span class="name">{{ row.nickname }}</span>
            <span class="pts">{{ row.battalion_points ?? row.season_points }} 贡献</span>
          </div>
          <el-empty v-if="!loading && !contribution.length" description="暂无同队球迷数据" />
        </template>

        <template v-else>
          <div v-for="(f, idx) in fanRank" :key="f.team" class="row">
            <span class="rank">{{ idx + 1 }}</span>
            <span class="name">{{ f.team }}</span>
            <span class="pts">{{ f.fans }} 铁粉</span>
          </div>
          <el-empty v-if="!loading && !fanRank.length" description="暂无数据" />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  getFanRank,
  getLeaderboardBoard,
  getLeaderboardRewardTiers,
  getMyLeaderboardSummary,
  type LeaderboardEntry,
  type LeaderboardRewardTier,
  type MyLeaderboardSummary,
} from '../api/commerce'
import { getStarAccuracy, getStarHeat, type StarHeatRow } from '../api/arena'
import { getTeamContribution, getTeams } from '../api/profile'
import { authState, fetchMe, isLoggedIn } from '../stores/authStore'
import { getReferralLeaderboard, type ReferralLeaderboardRow } from '../api/referral'
import { showApiError } from '../utils/errorHandler'
import { useInviteShare } from '../composables/useInviteShare'
import InvitePromptBar from '../components/InvitePromptBar.vue'
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({
  title: '球迷排行榜 — 最后一舞',
  description: '2026 世界杯球迷娱乐排行榜：竞猜积分、军团贡献、猜中率与召友榜。',
  path: '/leaderboard',
})

const { openShareSheet } = useInviteShare()

const route = useRoute()
const board = ref('points')
const period = ref('season')
const unifiedRows = ref<LeaderboardEntry[]>([])
const referralRows = ref<ReferralLeaderboardRow[]>([])
const referralPeriodLabel = ref('')
const referralMyRank = ref<number | null>(null)
const referralMyScore = ref(0)
const referralCountdown = ref('')
const boardDescription = ref('')
const periodLabel = ref('')
const mySummary = ref<MyLeaderboardSummary | null>(null)
const starRows = ref<StarHeatRow[]>([])
const accuracyRows = ref<any[]>([])
const fanRank = ref<{ team: string; fans: number }[]>([])
const contribution = ref<{ user_id: number; nickname: string; season_points: number; battalion_points?: number }[]>([])
const loading = ref(false)
const rewardTiers = ref<{ tiers: LeaderboardRewardTier[] } | null>(null)
const teamOptions = ref<{ id: number; name: string }[]>([])
const supporterTeamId = ref<number | null>(null)

const showSeasonRewards = computed(() => board.value === 'points' && period.value === 'season')

const rewardTierPreview = computed(() => {
  const tiers = rewardTiers.value?.tiers ?? []
  return tiers.filter((t) => t.rank <= 3)
})

const boardTitle = computed(() => {
  const map: Record<string, string> = {
    points: '累计积分榜',
    redeem_points: '可用积分榜',
    predict_accuracy: '竞猜准度榜',
    battalion: '铁粉军团榜',
    supporter: '球队应援榜',
    star_heat: '球星热力榜',
    star_accuracy: '球星竞猜准度榜',
    contribution: '主队贡献榜',
    referral: '召友榜',
    duel_elo: '卡牌对决 ELO 榜',
    duel_wins: '卡牌对决胜场榜',
    fans: '主队粉丝榜',
  }
  return map[board.value] ?? '排行榜'
})

function formatPoints(row: LeaderboardEntry) {
  if (board.value === 'predict_accuracy') {
    return `${row.win_rate ?? 0}% (${row.wins}/${row.settled})`
  }
  if (board.value === 'duel_elo') {
    return `${row.points ?? row.duel_elo ?? 0} ELO`
  }
  if (board.value === 'duel_wins') {
    const elo = row.duel_elo ? ` · ELO ${row.duel_elo}` : ''
    return `${row.points ?? 0} 胜${elo}`
  }
  const pts = row.points ?? row.season_points ?? row.redeem_points ?? row.battalion_points ?? 0
  const unit = board.value === 'battalion' || board.value === 'supporter' ? '贡献' : '分'
  return `${pts} ${unit}`
}

function onBoardChange() {
  if (board.value === 'predict_accuracy' || board.value === 'duel_elo' || board.value === 'duel_wins') {
    period.value = 'season'
  }
  if (board.value === 'referral') {
    load()
    return
  }
  load()
}

async function loadMySummary() {
  if (!authState.accessToken) {
    mySummary.value = null
    return
  }
  try {
    mySummary.value = await getMyLeaderboardSummary()
  } catch {
    mySummary.value = null
  }
}

async function load() {
  loading.value = true
  try {
    if (authState.accessToken) await fetchMe()
    boardDescription.value = ''
    periodLabel.value = ''

    if (
      board.value === 'points' ||
      board.value === 'redeem_points' ||
      board.value === 'predict_accuracy' ||
      board.value === 'battalion' ||
      board.value === 'supporter' ||
      board.value === 'duel_elo' ||
      board.value === 'duel_wins'
    ) {
      const tid =
        board.value === 'battalion'
          ? authState.user?.favorite_team_id ?? undefined
          : board.value === 'supporter'
            ? supporterTeamId.value ?? undefined
            : undefined
      const data = await getLeaderboardBoard({
        board: board.value,
        period: period.value,
        team_id: tid,
      })
      unifiedRows.value = data.rows
      boardDescription.value = data.description
      periodLabel.value = data.period_label
    } else if (board.value === 'referral') {
      const data = await getReferralLeaderboard()
      referralRows.value = data.rows
      referralPeriodLabel.value = data.period_label
      referralMyRank.value = data.my_rank ?? null
      referralMyScore.value = data.my_score ?? 0
      if (data.seconds_until_settle != null) {
        const d = Math.floor(data.seconds_until_settle / 86400)
        const h = Math.floor((data.seconds_until_settle % 86400) / 3600)
        referralCountdown.value = `距周一结算还有 ${d} 天 ${h} 小时 · 仅计完成档案或首玩的有效邀请`
      } else {
        referralCountdown.value = ''
      }
      boardDescription.value = '本周有效邀请排行（好友需完成档案或首次竞猜/助威）'
      periodLabel.value = data.period_label
    } else if (board.value === 'star_heat') {
      const data = await getStarHeat('global')
      starRows.value = data.rows
    } else if (board.value === 'star_accuracy') {
      accuracyRows.value = await getStarAccuracy()
    } else if (board.value === 'contribution') {
      contribution.value = await getTeamContribution(authState.user?.favorite_team_id ?? undefined)
    } else {
      fanRank.value = await getFanRank()
    }
    await loadMySummary()
  } catch (e) {
    showApiError(e)
  } finally {
    loading.value = false
  }
}

function onLeaderboardRefresh() {
  load()
}

onMounted(async () => {
  const qBoard = route.query.board
  if (qBoard === 'referral') {
    board.value = 'referral'
  } else if (qBoard === 'supporter') {
    board.value = 'supporter'
  } else if (qBoard === 'duel_elo' || qBoard === 'duel_wins') {
    board.value = String(qBoard)
  }
  try {
    const teams = await getTeams()
    teamOptions.value = teams.map((t) => ({ id: t.id, name: t.name }))
    supporterTeamId.value =
      authState.user?.favorite_team_id ??
      authState.user?.secondary_team_id ??
      teamOptions.value[0]?.id ??
      null
  } catch {
    teamOptions.value = []
  }
  load()
  void getLeaderboardRewardTiers()
    .then((data) => {
      rewardTiers.value = data
    })
    .catch(() => {})
  window.addEventListener('leaderboard-refresh', onLeaderboardRefresh)
})

onUnmounted(() => {
  window.removeEventListener('leaderboard-refresh', onLeaderboardRefresh)
})
</script>

<style scoped>
.leaderboard {
  padding: 20px;
  max-width: 960px;
  margin: 0 auto;
}
.header {
  padding: 20px;
  margin-bottom: 20px;
}
.header h1 {
  margin: 0 0 8px;
}
.header p {
  margin: 0 0 16px;
  color: var(--wc-text-muted);
  font-size: 0.9rem;
}
.season-rewards {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(232, 197, 71, 0.25);
  border-radius: 12px;
}
.season-rewards-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.season-rewards-head .trophy {
  font-size: 1.6rem;
  line-height: 1;
}
.season-rewards-head strong {
  display: block;
  color: var(--wc-accent-gold);
  font-size: 0.92rem;
  margin-bottom: 4px;
}
.season-rewards-head p {
  margin: 0;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  line-height: 1.45;
}
.tier-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tier-chip {
  flex: 1;
  min-width: 140px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(61, 214, 140, 0.2);
}
.tier-rank {
  display: block;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  margin-bottom: 2px;
}
.tier-reward {
  font-size: 0.82rem;
  font-weight: 600;
  color: #f5f0e8;
}
.tier-more {
  margin: 10px 0 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.my-summary {
  margin: 16px 0;
  padding: 14px 16px;
  border-radius: 12px;
}
.my-title {
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  margin-bottom: 10px;
}
.my-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}
.my-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.my-stat .label {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}
.my-stat strong {
  font-size: 1.2rem;
  color: var(--wc-accent-gold);
}
.rank-tag {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.streak-hint {
  margin: 10px 0 0;
  font-size: 0.8rem;
  color: #6ec99a;
}
.gap-hint {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--wc-accent-rose, #c9788a);
}
.gap-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.period {
  margin-top: 12px;
}
.rule-hint {
  margin-top: 12px;
}
.my-ref-hint {
  margin-bottom: 10px;
}

.referral-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.supporter-team-pick {
  margin: 12px 0 4px;
  max-width: 220px;
}

.ref-countdown {
  margin-top: 12px;
}
.boards {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}
.board {
  padding: 20px;
}
.board h2 {
  margin: 0 0 16px;
  font-size: 1rem;
}
.period-label {
  font-weight: normal;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
}
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.row.me {
  background: rgba(212, 165, 116, 0.08);
  border-radius: 8px;
  padding-left: 8px;
  padding-right: 8px;
}
.me-tag {
  margin-left: 6px;
  font-size: 0.65rem;
  padding: 1px 5px;
  border-radius: 6px;
  background: rgba(212, 165, 116, 0.25);
  color: var(--wc-accent-gold);
}
.acc-block {
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.top-fans {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 0 8px 40px;
}
.fan-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
}
.rank {
  width: 28px;
  font-weight: 700;
  opacity: 0.7;
}
.rank.top {
  color: #d4a574;
  opacity: 1;
}
.tier {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  color: #d4a574;
}
.name {
  flex: 1;
}
.pts {
  color: #d4a574;
}
.sample {
  font-size: 11px;
  opacity: 0.6;
}
.streak {
  font-size: 12px;
}
.streak.mild {
  opacity: 0.75;
}

.board-tabs {
  margin-bottom: 12px;
}

@media (max-width: 768px) {
  .leaderboard.page-shell {
    padding: 12px;
  }
  .my-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .row {
    flex-wrap: wrap;
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .my-grid {
    grid-template-columns: 1fr;
  }
}
</style>
