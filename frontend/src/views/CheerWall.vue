<template>
  <div class="cheer-page" v-loading="loading">
    <div class="cheer-shell glass-panel" v-if="status">
      <header class="page-header">
        <h1>助威墙</h1>
        <p class="match-meta">
          {{ status.team1.name }}
          <span class="vs">VS</span>
          {{ status.team2.name }}
        </p>
        <p v-if="status.match_date" class="kickoff-hint">
          开球 {{ status.match_date }} {{ status.match_time || '' }}
        </p>
      </header>

      <section class="stat-block">
        <div class="block-head">
          <h2>双队擂台 · 军团战力</h2>
        </div>
        <CheerProgressBar
          :team1-name="status.team1.name"
          :team2-name="status.team2.name"
          :team1-cheers="status.arena.home_power"
          :team2-cheers="status.arena.away_power"
        />
        <p v-if="status.arena.leader_name" class="hint">
          🏆 {{ status.arena.leader_name }} 球迷领先 {{ status.arena.lead_points }} 点
        </p>
      </section>

      <section class="stat-block">
        <div class="block-head">
          <h2>助威值</h2>
        </div>
        <CheerProgressBar
          :team1-name="status.team1.name"
          :team2-name="status.team2.name"
          :team1-cheers="status.team1.cheers"
          :team2-cheers="status.team2.cheers"
        />
      </section>

      <p class="rule">
        开赛前 {{ status.cheer_close_minutes ?? 30 }} 分钟截止助威 ·
        <template v-if="status.free_cheer_tickets">你有 {{ status.free_cheer_tickets }} 张免费助威券（本次 0 币）</template>
        <template v-else>5 球迷币 = +10 助威值 +10 军团贡献</template>
        · 每场 1 次 · 只能为主队或副队助威
      </p>

      <!-- 可助威 -->
      <div v-if="status.can_cheer && !status.user_cheered && authState.user?.profile_completed" class="action-zone">
        <button
          v-if="canCheerTeam(status.team1.id)"
          type="button"
          class="cheer-btn"
          @click="cheer(status.team1.id)"
        >
          <span class="btn-icon">📣</span>
          为 {{ status.team1.name }} 助威
        </button>
        <button
          v-if="canCheerTeam(status.team2.id)"
          type="button"
          class="cheer-btn alt"
          @click="cheer(status.team2.id)"
        >
          <span class="btn-icon">📣</span>
          为 {{ status.team2.name }} 助威
        </button>
        <p v-if="!hasCheerTarget" class="status-box warn">
          你的主队/副队不在本场对阵中，无法助威。可在「球迷档案」调整副队。
        </p>
      </div>

      <!-- 未完善档案 -->
      <div v-else-if="!authState.user?.profile_completed" class="status-box warn">
        <p>完善球迷档案后即可助威</p>
        <button type="button" class="link-cta" @click="$router.push('/onboarding')">去完善档案 →</button>
      </div>

      <!-- 已助威 -->
      <div v-else-if="status.user_cheered" class="status-box success">
        <p>✅ 你已为本场助威，+10 军团贡献</p>
        <button
          v-if="!status.user_cheer_extra_done"
          type="button"
          class="extra-btn"
          @click="cheerExtra"
        >
          助威加码 · 10 币 +20 贡献
        </button>
        <small class="legal-hint">虚拟道具，不可提现</small>
      </div>

      <!-- 停止助威 -->
      <div v-else class="status-box muted">
        <p>{{ blockReasonText }}</p>
      </div>

      <button type="button" class="back-link" @click="$router.push('/arena')">← 返回球迷擂台</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import CheerProgressBar from '../components/CheerProgressBar.vue'
import { getCheerStatus, submitCheer } from '../api/profile'
import { boostCheerExtra } from '../api/arena'
import { authState, fetchMe } from '../stores/authStore'
import { fetchProfileStatus } from '../stores/profileStore'
import { getErrorMessage } from '../api/client'

const route = useRoute()
const loading = ref(false)
const status = ref<any>(null)

function canCheerTeam(teamId: number | null | undefined) {
  if (!teamId) return false
  const u = authState.user
  if (!u) return false
  return teamId === u.favorite_team_id || teamId === u.secondary_team_id
}

const hasCheerTarget = computed(() => {
  if (!status.value) return false
  return canCheerTeam(status.value.team1.id) || canCheerTeam(status.value.team2.id)
})

const blockReasonText = computed(() => {
  const s = status.value
  if (!s) return '本场已停止助威'
  const mins = s.cheer_close_minutes ?? 30
  switch (s.cheer_block_reason) {
    case 'match_started':
      return '比赛已开始或已结束，助威通道已关闭'
    case 'closed_before_kickoff':
      return `距开球不足 ${mins} 分钟，助威已截止（与竞猜截止规则一致）`
    case 'no_kickoff':
      return '该场比赛缺少有效开球时间，暂不可助威'
    default:
      return '本场已停止助威'
  }
})

async function load() {
  const id = Number(route.params.matchId)
  if (!id) return
  loading.value = true
  try {
    if (authState.accessToken) await fetchProfileStatus()
    status.value = await getCheerStatus(id)
  } catch (e) {
    ElMessage.error(getErrorMessage(e))
  } finally {
    loading.value = false
  }
}

async function cheer(teamId: number) {
  try {
    status.value = await submitCheer(Number(route.params.matchId), teamId)
    await fetchMe()
    await fetchProfileStatus(true)
    ElMessage.success('助威成功！+10 助威值 · +10 军团贡献')
  } catch (e) {
    ElMessage.error(getErrorMessage(e))
  }
}

async function cheerExtra() {
  try {
    await boostCheerExtra(Number(route.params.matchId))
    status.value = await getCheerStatus(Number(route.params.matchId))
    await fetchMe()
    ElMessage.success('助威加码成功 +20 军团贡献')
  } catch (e) {
    ElMessage.error(getErrorMessage(e))
  }
}

onMounted(load)
</script>

<style scoped>
.cheer-page {
  padding: 16px 20px 32px;
  max-width: 720px;
  margin: 0 auto;
  background: transparent;
}

.cheer-shell {
  padding: 22px 24px 26px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  text-align: center;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.match-meta {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #f5f0e8;
}

.match-meta .vs {
  margin: 0 10px;
  font-size: 0.85rem;
  color: var(--wc-accent-rose);
}

.kickoff-hint {
  margin: 8px 0 0;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
}

.stat-block {
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(12, 14, 28, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.block-head h2 {
  margin: 0 0 12px;
  font-size: 0.92rem;
  font-weight: 700;
  color: #f0d9b5;
}

.hint {
  margin: 10px 0 0;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.75);
  text-align: center;
}

.rule {
  margin: 0;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.2);
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.72);
  text-align: center;
  line-height: 1.5;
}

.action-zone {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cheer-btn {
  width: 100%;
  padding: 16px 20px;
  border: none;
  border-radius: 12px;
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  color: #1a1208;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 45%, #e8b86d 100%);
  box-shadow:
    0 0 0 1px rgba(255, 220, 160, 0.5),
    0 4px 20px rgba(212, 165, 116, 0.55),
    0 0 32px rgba(212, 165, 116, 0.25);
  transition: transform 0.15s, box-shadow 0.2s;
}

.cheer-btn.alt {
  background: linear-gradient(135deg, rgba(240, 217, 181, 0.95) 0%, rgba(201, 120, 138, 0.85) 100%);
  box-shadow:
    0 0 0 1px rgba(201, 120, 138, 0.4),
    0 4px 18px rgba(201, 120, 138, 0.35);
}

.cheer-btn:hover {
  transform: translateY(-2px) scale(1.01);
}

.cheer-btn:active {
  transform: translateY(0) scale(0.99);
}

.btn-icon {
  font-size: 1.2rem;
}

.status-box {
  padding: 16px 18px;
  border-radius: 12px;
  text-align: center;
}

.status-box p {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.5;
}

.status-box.warn {
  background: rgba(230, 162, 60, 0.12);
  border: 1px solid rgba(230, 162, 60, 0.35);
  color: #ffd591;
}

.status-box.success {
  background: rgba(103, 194, 58, 0.12);
  border: 1px solid rgba(103, 194, 58, 0.35);
  color: #b7eb8f;
}

.status-box.muted {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.75);
}

.link-cta,
.extra-btn {
  margin-top: 12px;
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold);
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
}

.extra-btn {
  display: block;
  width: 100%;
  margin-top: 14px;
  color: #ffd591;
  border-color: rgba(230, 162, 60, 0.45);
  background: rgba(230, 162, 60, 0.12);
}

.legal-hint {
  display: block;
  margin-top: 8px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
}

.back-link {
  align-self: center;
  margin-top: 4px;
  padding: 8px 0;
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  font-size: 0.88rem;
  cursor: pointer;
}

.back-link:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .cheer-page {
    padding: 12px;
  }
  .action-zone {
    flex-direction: column;
  }
  .cheer-btn,
  .extra-btn {
    min-height: 44px;
  }
}
</style>
