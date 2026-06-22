<template>
  <details class="duel-playbook glass-panel">
    <summary class="playbook-summary">
      <span class="playbook-title">卡牌对决指南</span>
      <span class="playbook-sub">三局两胜 · 属性克制 · 快速匹配</span>
    </summary>
    <div class="playbook-body">
      <ul class="playbook-list">
        <li><strong>组牌</strong> — 选 3 张未锁定、未质押、已拆分的卡；同队 +3% 战力，含传奇 +2%</li>
        <li><strong>三局两胜</strong> — 每局 1v1 比六维加权战力；前锋/中场/后卫存在位置克制</li>
        <li><strong>练习 vs AI</strong> — 免费演练，AI 按你的卡组强度匹配真实球员卡</li>
        <li><strong>快速匹配</strong> — 5 分钟内匹配同档位玩家，自动开战</li>
        <li><strong>邀请好友</strong> — 输入对方邀请码发起挑战，对方选卡应战</li>
        <li><strong>智能组牌</strong> — 一键从可用卡中推荐战力+化学反应最优 3 张组合</li>
        <li><strong>ELO 排位</strong> — PVP 大幅波动、AI 练习小幅波动；青铜至大师段位</li>
      </ul>
      <div v-if="stats" class="stat-chips">
        <span v-if="stats.elo_tier" class="chip elo">{{ stats.elo_tier.label }} · {{ stats.duel_elo }}</span>
        <span class="chip">{{ stats.rank_tier?.label || '新秀' }}</span>
        <span class="chip">胜 {{ stats.wins }} / 负 {{ stats.losses }}</span>
        <span v-if="stats.win_rate" class="chip">胜率 {{ stats.win_rate }}%</span>
        <span v-if="stats.current_streak >= 2" class="chip hot">
          {{ stats.streak_type === 'win' ? '连胜' : '连败' }} {{ stats.current_streak }}
        </span>
      </div>
      <div v-if="eloLeaderboard.length" class="lb-mini">
        <span class="lb-title">ELO 排位榜</span>
        <ol>
          <li v-for="(row, i) in eloLeaderboard" :key="row.user_id">
            <span class="rank">{{ i + 1 }}</span> {{ row.nickname }} · {{ row.duel_elo }}
            <span v-if="row.elo_tier" class="tier-tag">{{ row.elo_tier.label }}</span>
          </li>
        </ol>
      </div>
      <div v-if="leaderboard.length" class="lb-mini">
        <span class="lb-title">对决胜场榜</span>
        <ol>
          <li v-for="(row, i) in leaderboard" :key="row.user_id">
            <span class="rank">{{ i + 1 }}</span> {{ row.nickname }} · {{ row.wins }} 胜
          </li>
        </ol>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDuelLeaderboard, getDuelStats, type DuelStats } from '@/api/asset'

const stats = ref<DuelStats | null>(null)
const leaderboard = ref<{ user_id: number; nickname: string; wins: number }[]>([])
const eloLeaderboard = ref<
  { user_id: number; nickname: string; duel_elo: number; elo_tier?: { label: string } }[]
>([])

onMounted(async () => {
  try {
    stats.value = await getDuelStats()
    const [winsLb, eloLb] = await Promise.all([
      getDuelLeaderboard(5, 'wins'),
      getDuelLeaderboard(5, 'elo'),
    ])
    leaderboard.value = winsLb as { user_id: number; nickname: string; wins: number }[]
    eloLeaderboard.value = eloLb as typeof eloLeaderboard.value
  } catch {
    /* guest or error */
  }
})
</script>

<style scoped>
.duel-playbook {
  padding: 0;
  margin-bottom: 12px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(232, 200, 138, 0.2);
}
.playbook-summary {
  list-style: none;
  cursor: pointer;
  padding: 12px 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
}
.playbook-summary::-webkit-details-marker {
  display: none;
}
.playbook-title {
  font-weight: 800;
  font-size: 0.9rem;
  color: #e8c88a;
}
.playbook-sub {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
}
.playbook-body {
  padding: 0 16px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.playbook-list {
  margin: 12px 0;
  padding-left: 1.1em;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.55;
}
.playbook-list strong {
  color: #f0d9b5;
}
.stat-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.chip {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.65);
}
.chip.hot {
  background: rgba(232, 93, 93, 0.15);
  color: #f0a0a0;
}
.chip.elo {
  background: rgba(232, 200, 138, 0.15);
  color: #e8c88a;
}
.tier-tag {
  margin-left: 4px;
  opacity: 0.75;
}
.lb-mini {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.6);
}
.lb-title {
  display: block;
  margin-bottom: 6px;
  color: rgba(255, 255, 255, 0.45);
}
.lb-mini ol {
  margin: 0;
  padding-left: 1.2em;
}
.lb-mini li {
  margin-bottom: 2px;
}
.rank {
  color: #e8c88a;
  font-weight: 700;
}
</style>
