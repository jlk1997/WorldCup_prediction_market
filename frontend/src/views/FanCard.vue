<template>
  <div class="fan-card-page page-shell" v-loading="loading">
    <div class="card glass-panel" v-if="card" :class="cardClasses">
      <div class="card-avatar-wrap" :class="avatarFrameClass(card.avatar_frame)">
        <span class="card-avatar-letter">{{ card.nickname.slice(0, 1) }}</span>
      </div>
      <p v-if="passActive" class="pass-until">
        赛季通行证 · 至 {{ formatPassUntil(authState.user?.season_pass_until) }}
      </p>
      <div class="card-top">
        <span class="level">Lv.{{ card.fan_level }}</span>
        <span v-if="card.badges?.length" class="badge">{{ card.badges[0].title }}</span>
      </div>
      <h1>{{ card.nickname }}</h1>
      <p class="tagline">{{ card.tagline }}</p>
      <div class="teams">
        <div v-if="card.main_team" class="team-row">
          <span class="tag main">主队</span>
          <strong>{{ card.main_team.name }}</strong>
        </div>
        <div v-if="card.secondary_team" class="team-row">
          <span class="tag sub">副队</span>
          <strong>{{ card.secondary_team.name }}</strong>
        </div>
      </div>
      <div class="stars">
        <span v-for="p in card.players" :key="p.id" class="star-chip">⭐ {{ p.name }}</span>
      </div>
      <div v-if="card.star_contributions?.length" class="heat-row">
        <span v-for="s in card.star_contributions" :key="s.player_id" class="heat-chip">
          🔥 {{ s.player_name }} {{ s.heat }}
        </span>
      </div>
      <div class="stats">
        <div><strong>{{ card.battalion_points ?? 0 }}</strong><span>军团贡献</span></div>
        <div><strong>{{ card.season_points }}</strong><span>累计积分</span></div>
        <div><strong>{{ card.redeem_points ?? 0 }}</strong><span>可用积分</span></div>
        <div><strong>{{ card.fan_cheers_total }}</strong><span>助威值</span></div>
        <div><strong>{{ card.win_rate }}%</strong><span>竞猜胜率</span></div>
      </div>
      <p v-if="card.arena_tier" class="tier-line">
        队内段位 · {{ tierLabel(card.arena_tier) }}
        <span v-if="card.team_rank"> · 排名第 {{ card.team_rank }}</span>
      </p>
      <p v-if="card.same_team_recruits" class="same-team-line">
        已与 {{ card.same_team_recruits }} 位好友同队扩编 🤝
      </p>
      <div class="actions">
        <el-button type="primary" plain @click="copyText">复制分享文案</el-button>
        <el-button plain @click="shareResult" :disabled="!card?.predictions_total">晒结果</el-button>
        <el-button plain @click="downloadPoster">生成分享海报</el-button>
        <el-button plain @click="$router.push('/me')">返回球迷中心</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getFanCard } from '../api/profile'
import { getReferralMe } from '../api/referral'
import { downloadSharePoster } from '../utils/sharePoster'
import { authState } from '../stores/authStore'
import { avatarFrameClass, formatPassUntil, hasActiveSeasonPass } from '../utils/entitlements'

const loading = ref(false)
const card = ref<any>(null)
const inviteLink = ref('')

const cardClasses = computed(() => ({
  pioneer: card.value?.arena_tier === 'pioneer',
  'theme-team_spirit': card.value?.theme_key === 'team_spirit',
  'framed-gold': card.value?.avatar_frame === 'gold_wc',
  'framed-silver': card.value?.avatar_frame === 'silver_wc',
  framed: !!card.value?.avatar_frame && !['gold_wc', 'silver_wc'].includes(card.value.avatar_frame),
}))

const passActive = computed(() => hasActiveSeasonPass(authState.user))

const tierLabels: Record<string, string> = {
  pioneer: '先锋',
  starter: '主力',
  bench: '替补',
  rookie: '新兵',
}

function tierLabel(code: string) {
  return tierLabels[code] ?? code
}

async function copyText() {
  if (!card.value) return
  const linkPart = inviteLink.value ? `\n${inviteLink.value}` : ''
  const text = `${card.value.nickname} · ${card.value.tagline}\n军团贡献 ${card.value.battalion_points ?? 0} · 累计积分 ${card.value.season_points} · 可用积分 ${card.value.redeem_points ?? 0} · 助威 ${card.value.fan_cheers_total}${linkPart}\n一起来「最后一舞」猜世界杯！（虚拟奖励不可提现）`
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('分享文案已复制')
  } catch {
    ElMessage.info(text)
  }
}

async function shareResult() {
  if (!card.value) return
  const text = `我在「最后一舞」竞猜胜率 ${card.value.win_rate}%（${card.value.predictions_total} 场）· 累计 ${card.value.season_points} 分\n${card.value.tagline}${inviteLink.value ? '\n' + inviteLink.value : ''}`
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('晒结果文案已复制')
  } catch {
    ElMessage.info(text)
  }
}

async function downloadPoster() {
  if (!card.value) return
  try {
    await downloadSharePoster({
      title: card.value.nickname,
      subtitle: card.value.tagline,
      statsLine: `累计 ${card.value.season_points} 分 · 胜率 ${card.value.win_rate}% · 军团 ${card.value.battalion_points ?? 0}`,
      footer: '虚拟奖励不可提现 · 一起来猜世界杯',
      qrUrl: inviteLink.value || undefined,
    })
    ElMessage.success('海报已保存')
  } catch {
    ElMessage.error('海报生成失败，请稍后再试')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [c, refMe] = await Promise.all([getFanCard(), getReferralMe().catch(() => null)])
    card.value = c
    if (refMe?.invite_link) inviteLink.value = refMe.invite_link
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.fan-card-page {
  display: flex;
  justify-content: center;
  padding: 24px;
}
.card {
  max-width: 440px;
  width: 100%;
  padding: 28px;
  text-align: center;
  background: linear-gradient(145deg, rgba(139,41,66,0.25), rgba(212,165,116,0.12));
  border: 1px solid rgba(212, 165, 116, 0.25);
}
.card-top {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 8px;
}
.level {
  color: var(--wc-accent-gold);
  font-weight: 700;
}
.badge {
  padding: 2px 10px;
  border-radius: 12px;
  background: rgba(139, 41, 66, 0.35);
  font-size: 0.75rem;
}
.tagline { color: var(--wc-text-muted); margin: 12px 0 16px; line-height: 1.5; }
.team-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 6px;
}
.tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 8px;
}
.tag.main { background: rgba(212, 165, 116, 0.2); color: var(--wc-accent-gold); }
.tag.sub { background: rgba(255,255,255,0.08); color: var(--wc-text-muted); }
.stars { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 16px 0 20px; }
.star-chip {
  padding: 4px 12px;
  border-radius: 16px;
  background: rgba(255,255,255,0.08);
  font-size: 0.85rem;
}
.stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 24px;
  padding: 16px 0;
  border-top: 1px solid rgba(255,255,255,0.08);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.stats div { display: flex; flex-direction: column; gap: 4px; }
.stats strong { font-size: 1.5rem; color: var(--wc-accent-gold); }
.stats span { font-size: 0.75rem; color: var(--wc-text-muted); }
.card.pioneer {
  border-color: gold;
  box-shadow: 0 0 24px rgba(255, 215, 0, 0.15);
}
.card.theme-team_spirit {
  background: linear-gradient(145deg, rgba(212, 165, 116, 0.28), rgba(139, 41, 66, 0.2));
  border-color: rgba(232, 184, 74, 0.45);
}
.card.framed-gold {
  box-shadow: 0 0 0 2px rgba(232, 184, 74, 0.65), 0 0 24px rgba(212, 165, 116, 0.35);
}

.card.framed-silver {
  box-shadow: 0 0 0 2px rgba(192, 192, 192, 0.55), 0 0 18px rgba(200, 200, 200, 0.25);
}

.card.framed {
  box-shadow: 0 0 0 2px rgba(232, 184, 74, 0.5), 0 0 20px rgba(212, 165, 116, 0.2);
}

.card-avatar-wrap {
  width: 72px;
  height: 72px;
  margin: 0 auto 12px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(212, 165, 116, 0.15);
  border: 2px solid rgba(212, 165, 116, 0.35);
}

.card-avatar-wrap.frame-gold_wc {
  border: 3px solid #e8c88a;
  box-shadow: 0 0 0 2px rgba(232, 200, 138, 0.35), 0 0 16px rgba(212, 165, 116, 0.45);
}

.card-avatar-wrap.frame-silver_wc {
  border: 3px solid #c0c0c0;
  box-shadow: 0 0 0 2px rgba(192, 192, 192, 0.3), 0 0 12px rgba(200, 200, 200, 0.25);
}

.card-avatar-letter {
  font-size: 1.6rem;
  font-weight: 800;
  color: #f5f0e8;
}

.pass-until {
  margin: 0 0 8px;
  font-size: 0.78rem;
  color: #8fd48a;
}
.heat-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-bottom: 12px;
}
.heat-chip {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.15);
}
.same-team-line {
  margin: 8px 0 0;
  font-size: 0.85rem;
  color: #d4a574;
}
.tier-line {
  font-size: 0.85rem;
  color: var(--wc-accent-gold);
  margin-bottom: 16px;
}
.actions { display: flex; flex-direction: column; gap: 10px; }

@media (max-width: 768px) {
  .fan-card-page {
    padding: 12px;
  }
  .card {
    padding: 16px;
    margin: 8px;
  }
  .actions .el-button {
    width: 100%;
    min-height: 44px;
  }
}
</style>
