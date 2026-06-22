<template>
  <div class="arena-hub mobile-page page-shell" v-loading="loading">
    <header class="page-header">
      <h1>球迷擂台</h1>
      <p>军团贡献 · 球星热力 · 助威对决 · 虚拟娱乐不可提现</p>
    </header>

    <ArenaPlaybook
      v-if="overview"
      :stats="overview.quick_stats"
      :default-open="(overview.quick_stats?.today_cheerable ?? 0) > 0"
    />

    <section id="duel" class="glass-panel block card-duel-block">
      <div class="duel-section-head">
        <div>
          <h2 class="duel-section-title">⚔️ 卡牌对决</h2>
          <p class="duel-section-sub">三局两胜 · ELO 排位 · 智能组牌 · 快速匹配</p>
        </div>
        <router-link to="/leaderboard?board=duel_elo" class="duel-lb-link">ELO 排位榜 →</router-link>
      </div>
      <DuelPlaybook />
      <CardDuelPanel />
    </section>

    <div v-if="overview" class="arena-layout">
      <div class="col-main">
        <section class="glass-panel block standing-card" v-if="overview.standing.team_id">
          <div class="standing-head">
            <div class="tier-badge" :class="overview.standing.arena_tier">
              {{ overview.standing.tier_label }}
            </div>
            <span class="team-tag">队内排行</span>
          </div>
          <div class="standing-stats">
            <div class="stat-item">
              <span class="stat-label">排名</span>
              <span class="stat-value">
                {{ overview.standing.rank }}
                <small>/ {{ overview.standing.total_members }}</small>
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">军团贡献</span>
              <span class="stat-value gold">{{ overview.standing.battalion_points }}</span>
            </div>
            <div class="stat-item" v-if="overview.standing.gap_to_prev">
              <span class="stat-label">距上一名</span>
              <span class="stat-value">{{ overview.standing.gap_to_prev }} 点</span>
            </div>
            <div class="stat-item" v-if="overview.card_boost_pct > 0">
              <span class="stat-label">
                卡牌军团加成
                <el-tooltip placement="top">
                  <template #content>
                    持有主队队徽卡 +3%/张（上限9%）· 质押同队球员卡 +5%/张（上限15%）· 传奇卡额外 +2%
                    <br />前往收藏册持有/质押更多卡牌提升助威贡献
                  </template>
                  <span class="boost-hint">?</span>
                </el-tooltip>
              </span>
              <span class="stat-value boost">+{{ overview.card_boost_pct }}%</span>
            </div>
          </div>
        </section>
        <section v-else class="glass-panel block empty-team">
          <p>设置主队后可参与队内军团榜</p>
          <p class="empty-sub">未设主队也能：今日场次助威 · 临场口号 · 中立助阵 · 球队应援榜</p>
          <div class="empty-actions">
            <el-button type="primary" @click="$router.push('/onboarding')">去设置主队</el-button>
            <el-button plain @click="$router.push('/leaderboard?board=supporter')">看应援榜</el-button>
          </div>
        </section>

        <section class="glass-panel block" v-if="overview.next_match_arena">
          <div class="block-head">
            <h2>下一场擂台</h2>
            <span class="block-tag live">即将开赛</span>
          </div>
          <p class="match-title">
            {{ overview.next_match_arena.team1_name }}
            <span class="vs">VS</span>
            {{ overview.next_match_arena.team2_name }}
          </p>
          <CheerProgressBar
            :team1-name="overview.next_match_arena.home.name"
            :team2-name="overview.next_match_arena.away.name"
            :team1-cheers="overview.next_match_arena.home.power"
            :team2-cheers="overview.next_match_arena.away.power"
          />
          <p v-if="overview.next_match_arena.leader_name" class="lead-hint">
            🏆 {{ overview.next_match_arena.leader_name }} 球迷领先 {{ overview.next_match_arena.lead_points }} 点
          </p>
          <div class="cta-row">
            <button type="button" class="cta-btn cheer-cta" @click="$router.push(`/cheer/${overview.next_match_arena.match_id}`)">
              <span class="cta-icon">📣</span>
              去助威
            </button>
            <button type="button" class="cta-btn secondary" @click="$router.push('/predict')">去竞猜</button>
          </div>
        </section>

        <section class="glass-panel block" v-if="overview.matchday_goal.active">
          <div class="block-head">
            <h2>比赛日动员</h2>
            <span v-if="overview.matchday_goal.team_name" class="block-tag">{{ overview.matchday_goal.team_name }}</span>
          </div>
          <p class="block-desc">全队今日军团贡献进度（达标发虚拟称号与球迷币）</p>
          <el-progress :percentage="goalPct(overview.matchday_goal)" :stroke-width="12" status="success" />
          <p class="goal-progress">
            当前 <strong>{{ overview.matchday_goal.progress }}</strong> / 下一目标 <strong>{{ nextGoalFor(overview.matchday_goal) }}</strong>
          </p>
          <ul v-if="overview.matchday_goal.goal_titles" class="goal-tiers">
            <li v-for="(g, i) in overview.matchday_goal.goals" :key="g" :class="{ done: overview.matchday_goal.progress >= g }">
              {{ overview.matchday_goal.goal_titles[i] }} · {{ g }} 点
              <span v-if="overview.matchday_goal.progress >= g">✓</span>
            </li>
          </ul>
          <p v-if="overview.matchday_goal.my_titles?.length" class="my-titles">
            已获得：{{ overview.matchday_goal.my_titles.join('、') }}
          </p>
          <button
            v-if="!overview.matchday_goal.rally_done_today"
            type="button"
            class="cta-btn rally"
            @click="doRally(overview.matchday_goal.team_id)"
          >
            比赛日动员 · 20 币 +30 贡献
          </button>
          <p v-else class="rally-done">今日已为该队动员过</p>
          <p class="rally-hint">有机会获得该队球星数字藏品</p>
          <span class="legal-hint">虚拟道具，不可提现</span>
        </section>

        <section class="glass-panel block" v-if="overview.matchday_goal_secondary?.active">
          <div class="block-head">
            <h2>副队比赛日动员</h2>
            <span v-if="overview.matchday_goal_secondary.team_name" class="block-tag sub">{{ overview.matchday_goal_secondary.team_name }}</span>
          </div>
          <p class="block-desc">副队今日军团贡献进度</p>
          <el-progress :percentage="goalPct(overview.matchday_goal_secondary)" :stroke-width="12" status="success" />
          <p class="goal-progress">
            当前 <strong>{{ overview.matchday_goal_secondary.progress }}</strong> / 下一目标 <strong>{{ nextGoalFor(overview.matchday_goal_secondary) }}</strong>
          </p>
          <button
            v-if="!overview.matchday_goal_secondary.rally_done_today"
            type="button"
            class="cta-btn rally sub"
            @click="doRally(overview.matchday_goal_secondary.team_id)"
          >
            副队动员 · 20 币 +30 贡献
          </button>
          <p v-else class="rally-done">今日已为副队动员过</p>
          <span class="legal-hint">虚拟道具，不可提现</span>
        </section>

        <section class="glass-panel block today-matches" v-if="todayMatches.length">
          <div class="block-head">
            <h2>今日助威场次</h2>
            <button type="button" class="toggle-btn" @click="todayExpanded = !todayExpanded">
              {{ todayExpanded ? '收起' : '展开' }} ({{ todayMatches.length }})
            </button>
          </div>
          <div v-show="todayExpanded" class="today-list">
            <div v-for="m in todayMatches" :key="m.match_id" class="today-row">
              <div class="today-meta">
                <span class="today-teams">{{ m.team1_name }} VS {{ m.team2_name }}</span>
                <span v-if="m.match_time" class="today-time">{{ m.match_time }}</span>
              </div>
              <div v-if="m.predict_combo_pending || m.predict_combo_after_cheer" class="today-tags">
                <span v-if="m.predict_combo_pending" class="tag combo">竞猜后助威 · 连击+5</span>
                <span v-else-if="m.predict_combo_after_cheer" class="tag combo">助威后竞猜 · 连击+5</span>
              </div>
              <CheerProgressBar
                :team1-name="m.team1_name"
                :team2-name="m.team2_name"
                :team1-cheers="m.arena.home_power"
                :team2-cheers="m.arena.away_power"
              />
              <div class="today-actions">
                <button
                  v-if="m.user_cheered"
                  type="button"
                  class="mini-btn done"
                  disabled
                >
                  已助威
                </button>
                <button
                  v-else-if="m.can_cheer"
                  type="button"
                  class="mini-btn"
                  @click="$router.push(`/cheer/${m.match_id}`)"
                >
                  去助威
                </button>
                <span v-else class="mini-muted">已截止</span>
              </div>
            </div>
          </div>
        </section>

        <section
          class="glass-panel block spot-cheer"
          v-if="overview.spot_cheer?.teams_today?.length"
        >
          <div class="block-head">
            <h2>临场口号</h2>
            <span class="block-tag live">轻量应援</span>
          </div>
          <p class="block-desc">
            今日剩余 {{ overview.spot_cheer.remaining }}/{{ overview.spot_cheer.daily_limit }} 次 ·
            {{ overview.spot_cheer.cost }} 币 +{{ overview.spot_cheer.battalion_per_cheer }} 贡献/次
            <span v-if="overview.card_boost_pct > 0" class="card-boost-inline"> · 卡牌加成 +{{ overview.card_boost_pct }}%</span>
          </p>
          <div class="spot-dots" aria-hidden="true">
            <span
              v-for="i in overview.spot_cheer.daily_limit"
              :key="i"
              class="dot"
              :class="{ used: i <= overview.spot_cheer.used_today }"
            />
          </div>
          <div class="spot-row">
            <label class="spot-label">选择球队</label>
            <el-select v-model="spotTeamId" size="small" placeholder="今日参赛队">
              <el-option
                v-for="t in overview.spot_cheer.teams_today"
                :key="t.team_id"
                :label="t.team_name"
                :value="t.team_id"
              />
            </el-select>
          </div>
          <div class="slogan-chips">
            <button
              v-for="(s, i) in overview.spot_cheer.slogans"
              :key="i"
              type="button"
              class="slogan-chip"
              :class="{ active: spotSloganIndex === i }"
              @click="spotSloganIndex = i"
            >
              {{ s }}
            </button>
          </div>
          <button
            type="button"
            class="cta-btn rally"
            :disabled="!spotTeamId || overview.spot_cheer.remaining <= 0 || spotSubmitting"
            @click="doSpotCheer"
          >
            喊口号 · {{ overview.spot_cheer.cost }} 币
          </button>
          <span class="legal-hint">任意今日参赛队均可 · 非主队也能参与</span>
        </section>
      </div>

      <div class="col-side">
        <section class="glass-panel block" v-if="overview.my_stars.length">
          <h2>我的球星应援</h2>
          <div v-for="s in overview.my_stars" :key="s.player_id" class="star-row">
            <div class="star-info">
              <span class="star-name">{{ s.player_name }}</span>
              <span class="star-heat">热力 {{ s.my_heat ?? 0 }}</span>
            </div>
            <el-button
              v-if="s.can_boost_today"
              size="small"
              type="warning"
              plain
              @click="doBoostStar(s.player_id)"
            >
              应援 3 币
            </el-button>
          </div>
        </section>

        <section class="glass-panel block">
          <div class="block-head">
            <h2>球星热力</h2>
            <el-radio-group v-model="starScope" size="small" @change="loadStars">
              <el-radio-button value="my">我的球星</el-radio-button>
              <el-radio-button value="global">全站 Top</el-radio-button>
            </el-radio-group>
          </div>
          <div v-if="starRows.length" class="star-list">
            <div v-for="(row, idx) in starRows" :key="row.player_id" class="star-rank-row">
              <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
              <span class="name">{{ row.player_name }}</span>
              <span class="heat">{{ starScope === 'my' ? row.my_heat : row.global_heat }} 热力</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">🔥</span>
            <p>暂无热力数据</p>
            <small>助威、竞猜、球星应援都会累计热力</small>
          </div>
        </section>

        <section class="glass-panel block">
          <h2>球星竞猜准度</h2>
          <div v-if="accuracyRows.length" class="star-list">
            <div v-for="row in accuracyRows.slice(0, 5)" :key="row.player_id" class="star-rank-row">
              <span class="name">{{ row.player_name }}</span>
              <span class="heat">{{ row.accuracy_pct }}% <small>(n={{ row.sample_size }})</small></span>
            </div>
          </div>
          <div v-else class="empty-state compact">
            <span class="empty-icon">📊</span>
            <p>样本不足</p>
          </div>
          <button type="button" class="link-btn" @click="$router.push('/leaderboard')">查看完整准度榜 →</button>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({ title: '球迷擂台 — 最后一舞', path: '/arena', noIndex: true })

import CheerProgressBar from '../components/CheerProgressBar.vue'
import ArenaPlaybook from '../components/ArenaPlaybook.vue'
import CardDuelPanel from '../components/asset/CardDuelPanel.vue'
import DuelPlaybook from '../components/asset/DuelPlaybook.vue'
import {
  boostStar,
  getArenaOverview,
  getStarAccuracy,
  getStarHeat,
  getTodayMatches,
  matchdayRally,
  submitSpotCheer,
  type MatchdayGoal,
  type StarHeatRow,
  type TodayMatchRow,
} from '../api/arena'
import { fetchMe } from '../stores/authStore'
import { showApiError } from '../utils/errorHandler'
import { openCollectibleReveal } from '../stores/collectibleRevealStore'
import type { CollectibleDropResult } from '../api/collectible'

const loading = ref(false)
const overview = ref<Awaited<ReturnType<typeof getArenaOverview>> | null>(null)
const todayMatches = ref<TodayMatchRow[]>([])
const todayExpanded = ref(true)
const spotTeamId = ref<number | null>(null)
const spotSloganIndex = ref(0)
const spotSubmitting = ref(false)
const starScope = ref<'my' | 'global'>('my')
const starRows = ref<StarHeatRow[]>([])
const accuracyRows = ref<any[]>([])

function nextGoalFor(g: MatchdayGoal | undefined) {
  if (!g?.active) return 0
  for (const t of g.goals) {
    if (g.progress < t) return t
  }
  return g.goals[g.goals.length - 1]
}

function goalPct(g: MatchdayGoal | undefined) {
  const target = nextGoalFor(g)
  if (!g?.active || !target) return 0
  return Math.min(100, Math.round((g.progress / target) * 100))
}

async function load() {
  loading.value = true
  try {
    overview.value = await getArenaOverview()
    todayMatches.value = await getTodayMatches().catch(() => [])
    if (overview.value?.spot_cheer?.teams_today?.length && !spotTeamId.value) {
      spotTeamId.value = overview.value.spot_cheer.teams_today[0].team_id
    }
    await loadStars()
    accuracyRows.value = await getStarAccuracy()
  } catch (e) {
    showApiError(e)
  } finally {
    loading.value = false
  }
}

async function loadStars() {
  const data = await getStarHeat(starScope.value)
  starRows.value = data.rows
}

async function doBoostStar(playerId: number) {
  try {
    await boostStar(playerId)
    await fetchMe()
    ElMessage.success('球星应援成功')
    await load()
  } catch (e) {
    showApiError(e)
  }
}

async function doSpotCheer() {
  if (!spotTeamId.value) return
  spotSubmitting.value = true
  try {
    const res = await submitSpotCheer(spotTeamId.value, spotSloganIndex.value)
    await fetchMe()
    ElMessage.success(`「${res.slogan}」+${res.battalion_added} 军团贡献`)
    if (overview.value) overview.value.spot_cheer = res.spot_cheer
    await load()
  } catch (e) {
    showApiError(e)
  } finally {
    spotSubmitting.value = false
  }
}

async function doRally(teamId?: number) {
  try {
    const res = await matchdayRally(teamId)
    await fetchMe()
    ElMessage.success('动员成功')
    const drop = res.collectible_drop as CollectibleDropResult | null | undefined
    if (drop?.dropped) {
      openCollectibleReveal(drop, { subtitle: '比赛日动员奖励' })
    }
    await load()
  } catch (e) {
    showApiError(e)
  }
}

const route = useRoute()

onMounted(async () => {
  await load()
  if (route.hash === '#duel' || route.query.tab === 'duel') {
    requestAnimationFrame(() => {
      document.getElementById('duel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }
})
</script>

<style scoped>
.arena-hub {
  padding: 16px 20px 32px;
  max-width: 1080px;
  margin: 0 auto;
  background: transparent;
}

.page-header {
  margin-bottom: 18px;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-header p {
  margin: 0;
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.68);
}

.arena-layout {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 16px;
  align-items: start;
}

@media (max-width: 900px) {
  .arena-layout {
    grid-template-columns: 1fr;
  }
}

.block {
  padding: 18px 20px;
  margin-bottom: 16px;
}

.card-duel-block {
  border: 1px solid rgba(126, 184, 255, 0.28);
  background: linear-gradient(165deg, rgba(12, 18, 40, 0.95) 0%, rgba(8, 12, 28, 0.88) 100%);
  box-shadow: 0 8px 32px rgba(30, 60, 120, 0.2);
}

.duel-section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px 16px;
  margin-bottom: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(126, 184, 255, 0.15);
}

.duel-section-title {
  margin: 0 0 4px;
  font-size: 1.15rem;
  font-weight: 800;
  color: #e8c88a;
}

.duel-section-sub {
  margin: 0;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.55);
}

.duel-lb-link {
  font-size: 0.78rem;
  color: #9ec8ff;
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(126, 184, 255, 0.3);
  background: rgba(126, 184, 255, 0.08);
  white-space: nowrap;
}

.duel-lb-link:hover {
  color: #e8c88a;
  border-color: rgba(232, 200, 138, 0.4);
}

.block h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #f0d9b5;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.block-tag {
  font-size: 0.72rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(201, 120, 138, 0.15);
  color: #f0a0b0;
  border: 1px solid rgba(201, 120, 138, 0.35);
}

.block-tag.live {
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
  border-color: rgba(212, 165, 116, 0.35);
}

.block-tag.sub {
  background: rgba(120, 160, 200, 0.15);
  color: #a8c8e8;
  border-color: rgba(120, 160, 200, 0.35);
}

.block-desc {
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
}

.empty-team {
  text-align: center;
}

.empty-sub {
  margin: 8px 0 14px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.5;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

.today-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.today-tags .tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(103, 194, 58, 0.12);
  color: #b7eb8f;
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.spot-dots {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.spot-dots .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(212, 165, 116, 0.25);
  border: 1px solid rgba(212, 165, 116, 0.4);
}

.spot-dots .dot.used {
  background: var(--wc-accent-gold);
}

.standing-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.team-tag {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.5);
}

.standing-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

@media (max-width: 520px) {
  .standing-stats {
    grid-template-columns: 1fr;
  }
}

.stat-item {
  padding: 12px;
  border-radius: 10px;
  background: rgba(12, 14, 28, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-label {
  display: block;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: #f5f0e8;
}

.stat-value small {
  font-size: 0.85rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.45);
}

.stat-value.gold {
  color: var(--wc-accent-gold);
}

.stat-value.boost {
  color: #7dd3a8;
}

.boost-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  margin-left: 4px;
  border-radius: 50%;
  font-size: 0.62rem;
  background: rgba(255, 255, 255, 0.12);
  color: var(--wc-text-muted);
  cursor: help;
}

.card-boost-inline {
  color: #7dd3a8;
  font-weight: 600;
}

.tier-badge {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1px solid rgba(212, 165, 116, 0.45);
  color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.1);
}

.tier-badge.pioneer {
  border-color: gold;
  color: gold;
  background: rgba(255, 215, 0, 0.1);
}

.tier-badge.starter {
  border-color: #c0c0c0;
  color: #e8e8e8;
}

.empty-team {
  text-align: center;
  padding: 28px 20px;
  color: rgba(255, 255, 255, 0.7);
}

.match-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 14px;
  color: #f5f0e8;
  text-align: center;
}

.match-title .vs {
  margin: 0 8px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--wc-accent-rose);
}

.lead-hint {
  margin-top: 10px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.75);
  text-align: center;
}

.cta-row {
  margin-top: 18px;
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: stretch;
}

.cta-btn {
  min-width: 120px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(18, 22, 36, 0.75);
  color: #f5f0e8;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, transform 0.15s, box-shadow 0.2s;
}

.cta-btn:hover {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.12);
  transform: translateY(-1px);
}

.cta-btn.cheer-cta {
  flex: 1;
  max-width: 220px;
  min-width: 160px;
  padding: 14px 24px;
  border: none;
  border-radius: 12px;
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #1a1208;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 45%, #e8b86d 100%);
  box-shadow:
    0 0 0 1px rgba(255, 220, 160, 0.5),
    0 4px 20px rgba(212, 165, 116, 0.55),
    0 0 32px rgba(212, 165, 116, 0.25);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.cta-btn.cheer-cta .cta-icon {
  font-size: 1.15rem;
  line-height: 1;
}

.cta-btn.cheer-cta:hover {
  transform: translateY(-2px) scale(1.02);
  background: linear-gradient(135deg, #ffe8c8 0%, #e8c088 45%, #f0c878 100%);
  box-shadow:
    0 0 0 1px rgba(255, 230, 180, 0.7),
    0 6px 28px rgba(212, 165, 116, 0.65),
    0 0 40px rgba(212, 165, 116, 0.35);
}

.cta-btn.cheer-cta:active {
  transform: translateY(0) scale(0.99);
}

.cta-btn.secondary {
  flex: 0 0 auto;
  padding: 14px 20px;
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(12, 14, 28, 0.5);
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.88rem;
  font-weight: 600;
}

.cta-btn.secondary:hover {
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.06);
  color: #f5f0e8;
}

.cta-btn.rally {
  width: 100%;
  margin-top: 12px;
  margin-bottom: 6px;
  border-color: rgba(230, 162, 60, 0.45);
  color: #ffd591;
}
.cta-btn.rally.sub {
  border-color: rgba(120, 160, 200, 0.45);
  color: #a8c8e8;
}

.rally-done {
  margin: 12px 0 6px;
  font-size: 0.85rem;
  color: rgba(143, 212, 138, 0.9);
  text-align: center;
}

.today-matches .toggle-btn {
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.78rem;
  cursor: pointer;
}

.today-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 12px;
}

.today-row {
  padding: 12px;
  border-radius: 10px;
  background: rgba(12, 14, 28, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.today-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.today-teams {
  font-size: 0.9rem;
  font-weight: 700;
  color: #f5f0e8;
}

.today-time {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.5);
}

.today-actions {
  display: flex;
  justify-content: flex-end;
}

.mini-btn {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.mini-btn.done {
  opacity: 0.6;
  cursor: default;
}

.mini-muted {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.45);
}

.spot-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.spot-label {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.55);
}

.slogan-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.slogan-chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.82rem;
  cursor: pointer;
}

.slogan-chip.active {
  border-color: rgba(212, 165, 116, 0.55);
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold);
}

.rally-hint {
  margin: 0 0 12px;
  font-size: 0.72rem;
  color: rgba(126, 184, 255, 0.9);
  text-align: center;
}

.goal-progress {
  margin: 10px 0;
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.75);
}

.goal-progress strong {
  color: var(--wc-accent-gold);
}

.goal-tiers {
  margin: 8px 0 12px;
  padding: 0;
  list-style: none;
  font-size: 0.82rem;
}

.goal-tiers li {
  padding: 6px 0;
  color: rgba(255, 255, 255, 0.55);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.goal-tiers li.done {
  color: #8fd48a;
}

.my-titles {
  color: var(--wc-accent-gold);
  font-size: 0.85rem;
  margin-bottom: 8px;
}

.legal-hint {
  display: block;
  margin-top: 8px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
  text-align: center;
}

.star-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.star-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.star-name {
  font-weight: 600;
  color: #f5f0e8;
}

.star-heat {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.55);
}

.star-list {
  margin-top: 8px;
}

.star-rank-row {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.star-rank-row .rank {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.6);
}

.star-rank-row .rank.top {
  background: linear-gradient(135deg, #d4a574, #c9788a);
  color: #1a1208;
}

.star-rank-row .name {
  font-weight: 600;
  color: #f5f0e8;
}

.star-rank-row .heat {
  font-size: 0.82rem;
  color: var(--wc-accent-gold);
  white-space: nowrap;
}

.star-rank-row .heat small {
  color: rgba(255, 255, 255, 0.45);
}

.empty-state {
  text-align: center;
  padding: 28px 12px;
  color: rgba(255, 255, 255, 0.55);
}

.empty-state.compact {
  padding: 16px 12px;
}

.empty-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 8px;
}

.empty-state p {
  margin: 0 0 4px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.empty-state small {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.45);
}

.link-btn {
  margin-top: 12px;
  padding: 0;
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  font-size: 0.85rem;
  cursor: pointer;
}

.link-btn:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .arena-hub {
    padding: 12px;
  }
  .block-head {
    flex-direction: column;
    align-items: flex-start;
  }
  .cta-row {
    flex-direction: column;
  }
  .cta-btn,
  .cta-btn.cheer-cta {
    width: 100%;
    max-width: none;
    min-width: 0;
    min-height: 44px;
  }
}
</style>
