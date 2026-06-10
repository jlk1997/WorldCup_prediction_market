<template>
  <div class="arena-hub" v-loading="loading">
    <header class="page-header">
      <h1>球迷擂台</h1>
      <p>军团贡献 · 球星热力 · 助威对决 · 虚拟娱乐不可提现</p>
    </header>

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
          </div>
        </section>
        <section v-else class="glass-panel block empty-team">
          <p>设置主队后即可参与军团榜</p>
          <el-button type="primary" @click="$router.push('/onboarding')">去设置主队</el-button>
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
          </div>
          <p class="block-desc">全队今日军团贡献进度（达标发虚拟称号与球迷币）</p>
          <el-progress :percentage="goalPct" :stroke-width="12" status="success" />
          <p class="goal-progress">
            当前 <strong>{{ overview.matchday_goal.progress }}</strong> / 下一目标 <strong>{{ nextGoal }}</strong>
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
          <button type="button" class="cta-btn rally" @click="doRally">比赛日动员 · 20 币 +30 贡献</button>
          <span class="legal-hint">虚拟道具，不可提现</span>
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import CheerProgressBar from '../components/CheerProgressBar.vue'
import {
  boostStar,
  getArenaOverview,
  getStarAccuracy,
  getStarHeat,
  matchdayRally,
  type StarHeatRow,
} from '../api/arena'
import { fetchMe } from '../stores/authStore'
import { getErrorMessage } from '../api/client'

const loading = ref(false)
const overview = ref<Awaited<ReturnType<typeof getArenaOverview>> | null>(null)
const starScope = ref<'my' | 'global'>('my')
const starRows = ref<StarHeatRow[]>([])
const accuracyRows = ref<any[]>([])

const nextGoal = computed(() => {
  const g = overview.value?.matchday_goal
  if (!g?.active) return 0
  for (const t of g.goals) {
    if (g.progress < t) return t
  }
  return g.goals[g.goals.length - 1]
})

const goalPct = computed(() => {
  const g = overview.value?.matchday_goal
  if (!g?.active || !nextGoal.value) return 0
  return Math.min(100, Math.round((g.progress / nextGoal.value) * 100))
})

async function load() {
  loading.value = true
  try {
    overview.value = await getArenaOverview()
    await loadStars()
    accuracyRows.value = await getStarAccuracy()
  } catch (e) {
    ElMessage.error(getErrorMessage(e))
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
    ElMessage.error(getErrorMessage(e))
  }
}

async function doRally() {
  try {
    await matchdayRally()
    await fetchMe()
    ElMessage.success('动员成功')
    await load()
  } catch (e) {
    ElMessage.error(getErrorMessage(e))
  }
}

onMounted(load)
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

.block-desc {
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
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
  border-color: rgba(230, 162, 60, 0.45);
  color: #ffd591;
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
