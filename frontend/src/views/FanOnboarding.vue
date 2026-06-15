<template>
  <div class="onboarding">
    <div class="panel glass-panel">
      <el-alert
        v-if="fromReferral && !inviteeJourney"
        type="success"
        :closable="false"
        show-icon
        class="invitee-banner"
        title="你通过好友邀请加入 · 完成下面步骤，你和邀请人都能得奖励"
      />
      <el-alert
        v-if="inviteeJourney"
        type="success"
        :closable="false"
        show-icon
        class="invitee-banner"
      >
        <template #title>
          {{ inviteeJourney.inviter_nickname }} 邀请你加入 · 完成下面步骤还有奖励
        </template>
        下一步：{{ inviteeJourney.next_step?.label || '已全部完成，感谢参与' }}
        <el-button
          v-if="inviteeJourney.next_step?.action"
          link
          type="primary"
          @click="$router.push(inviteeJourney.next_step!.action!)"
        >
          去完成
        </el-button>
      </el-alert>
      <div class="progress">步骤 {{ step + 1 }} / 4</div>
      <h1>{{ titles[step] }}</h1>
      <p class="sub">{{ subs[step] }}</p>

      <TeamPickerGrid
        v-if="step === 0"
        v-model="mainTeamId"
        :teams="teams"
      />
      <TeamPickerGrid
        v-if="step === 1"
        v-model="subTeamId"
        :teams="teams"
        :exclude-id="mainTeamId"
      />
      <PlayerPickerChips
        v-if="step === 2"
        v-model="playerIds"
        :players="players"
      />
      <div v-if="step === 3" class="done-step">
        <div class="done-badge">
          <el-icon class="done-icon" :size="36"><CircleCheckFilled /></el-icon>
          <p class="done-lead">你的球迷身份已就绪！</p>
        </div>

        <div v-if="identitySummary.length" class="identity-row">
          <span v-for="chip in identitySummary" :key="chip" class="identity-chip">{{ chip }}</span>
        </div>

        <template v-if="recs?.cta?.length">
          <p class="cta-heading">为你推荐的下一步</p>
          <div class="cta-cards">
            <button
              v-for="c in recs.cta.slice(0, 3)"
              :key="c.path"
              type="button"
              class="cta-card"
              @click="go(c.path)"
            >
              <span class="cta-icon" aria-hidden="true">{{ ctaEmoji(c.type) }}</span>
              <span class="cta-label">{{ c.label }}</span>
              <el-icon class="cta-arrow"><ArrowRight /></el-icon>
            </button>
          </div>
        </template>
        <p v-else class="cta-empty">档案已保存，进入首页开始探索吧</p>
      </div>

      <div class="footer">
        <el-button text @click="skip">跳过</el-button>
        <el-button v-if="step > 0 && step < 3" plain @click="step--">上一步</el-button>
        <el-button v-if="step === 1" plain @click="step++">跳过副队</el-button>
        <el-button type="primary" :loading="loading" @click="next">
          {{ step === 3 ? '进入赛事大屏' : '下一步' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, CircleCheckFilled } from '@element-plus/icons-vue'
import TeamPickerGrid from '../components/TeamPickerGrid.vue'
import PlayerPickerChips from '../components/PlayerPickerChips.vue'
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({ title: '完善球迷档案 — 最后一舞', path: '/onboarding', noIndex: true })

import { getTeams, getPlayersForTeams, setupProfile, getRecommendations, type TeamBrief, type PlayerBrief } from '../api/profile'
import { getReferralMe, type InviteeJourney } from '../api/referral'
import { fetchMe } from '../stores/authStore'
import { fetchProfileStatus } from '../stores/profileStore'
import { showApiError } from '../utils/errorHandler'

const router = useRouter()
const route = useRoute()
const fromReferral = computed(() => route.query.from === 'referral')
const step = ref(0)
const teams = ref<TeamBrief[]>([])
const players = ref<PlayerBrief[]>([])
const mainTeamId = ref<number | null>(null)
const subTeamId = ref<number | null>(null)
const playerIds = ref<number[]>([])
const loading = ref(false)
const recs = ref<Awaited<ReturnType<typeof getRecommendations>> | null>(null)
const inviteeJourney = ref<InviteeJourney | null>(null)

const titles = ['选择你的主队', '选择副队（可选）', 'Pick 3 名最爱球星', '欢迎加入最后一舞']
const subs = [
  '主队将决定大屏优先展示、比赛日签到加成与助威归属',
  '副队比赛也会出现在「我的球队」视图',
  '球星所在场次会特别提醒你',
  '根据你的选择，我们准备了专属入口',
]

const identitySummary = computed(() => {
  const fi = recs.value?.fan_identity
  if (!fi) return []
  const chips: string[] = []
  if (fi.main_team?.name) chips.push(`主队 · ${fi.main_team.name}`)
  if (fi.secondary_team?.name) chips.push(`副队 · ${fi.secondary_team.name}`)
  if (fi.players?.length) chips.push(`球星 · ${fi.players.length} 人`)
  return chips
})

function ctaEmoji(type: string) {
  const map: Record<string, string> = {
    predict: '🎯',
    cheer: '📣',
    arena: '🏟️',
    agent: '🤖',
    onboarding: '📝',
  }
  return map[type] || '⚽'
}

async function loadPlayers() {
  const ids = [mainTeamId.value, subTeamId.value].filter((x): x is number => !!x)
  if (!ids.length) {
    players.value = []
    return
  }
  players.value = await getPlayersForTeams(ids)
}

async function next() {
  if (step.value === 0) {
    if (!mainTeamId.value) {
      ElMessage.warning('请选择主队')
      return
    }
    step.value++
    return
  }
  if (step.value === 1) {
    await loadPlayers()
    step.value++
    return
  }
  if (step.value === 2) {
    if (playerIds.value.length < 1) {
      ElMessage.warning('请至少选择 1 名球星')
      return
    }
    loading.value = true
    try {
      await setupProfile({
        main_team_id: mainTeamId.value!,
        secondary_team_id: subTeamId.value || null,
        player_ids: playerIds.value,
      })
      await fetchMe()
      await fetchProfileStatus(true)
      recs.value = await getRecommendations()
      try {
        const refMe = await getReferralMe()
        inviteeJourney.value = refMe.invitee_journey ?? null
      } catch {
        /* optional */
      }
      ElMessage.success(
        inviteeJourney.value ? '档案完成！邀请奖励已发放或即将到账' : '档案设置成功'
      )
      step.value++
    } catch (e) {
      showApiError(e)
    } finally {
      loading.value = false
    }
    return
  }
  if (step.value === 3) {
    router.replace('/')
    return
  }
}

const KEY_SKIP_HINT = 'wc_skip_profile_hint'

function skip() {
  localStorage.setItem(KEY_SKIP_HINT, '1')
  router.replace('/')
}

function go(path: string) {
  router.push(path)
}

onMounted(async () => {
  teams.value = await getTeams()
  try {
    const refMe = await getReferralMe()
    inviteeJourney.value = refMe.invitee_journey ?? null
  } catch {
    inviteeJourney.value = null
  }
})
</script>

<style scoped>
.onboarding {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--wc-header-height));
  padding: 20px;
  background: transparent;
}

.panel {
  max-width: 720px;
  width: 100%;
  padding: 28px 28px 24px;
}

.panel h1 {
  margin: 0 0 10px;
  font-size: 1.65rem;
  font-weight: 800;
  color: #f5f0e8;
  letter-spacing: 0.5px;
}

.invitee-banner {
  margin-bottom: 16px;
}

.progress {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--wc-accent-gold);
  margin-bottom: 10px;
}

.sub {
  color: rgba(255, 255, 255, 0.78);
  margin-bottom: 22px;
  font-size: 0.95rem;
  line-height: 1.55;
}

.footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 28px;
  flex-wrap: wrap;
}

.done-step {
  margin-top: 8px;
}

.done-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  margin-bottom: 20px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.14) 0%, rgba(201, 120, 138, 0.08) 100%);
  border: 1px solid rgba(212, 165, 116, 0.35);
}

.done-icon {
  color: #e8c88a;
  filter: drop-shadow(0 0 10px rgba(232, 200, 138, 0.45));
}

.done-lead {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #fff;
  text-align: center;
}

.identity-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
  justify-content: center;
}

.identity-chip {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #f0d9b5;
  background: rgba(212, 165, 116, 0.12);
  border: 1px solid rgba(212, 165, 116, 0.28);
}

.cta-heading {
  margin: 0 0 12px;
  font-size: 0.9rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 0.5px;
}

.cta-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cta-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(18, 22, 36, 0.85);
  cursor: pointer;
  text-align: left;
  color: #fff;
  transition: border-color 0.2s, background 0.2s, transform 0.15s;
}

.cta-card:hover {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.12);
  transform: translateY(-1px);
}

.cta-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.15);
}

.cta-label {
  flex: 1;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.45;
  color: #f5f0e8;
}

.cta-arrow {
  flex-shrink: 0;
  color: var(--wc-accent-gold);
  font-size: 1rem;
}

.cta-empty {
  margin: 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.92rem;
}

@media (max-width: 768px) {
  .onboarding {
    padding: 12px;
  }
  .panel {
    padding: 16px;
    margin: 8px;
  }
  .footer {
    flex-direction: column;
    align-items: stretch;
  }
  .footer .el-button {
    width: 100%;
    min-height: 44px;
    margin-left: 0 !important;
  }
}
</style>
