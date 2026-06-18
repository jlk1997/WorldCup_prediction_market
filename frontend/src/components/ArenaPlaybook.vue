<template>
  <details class="arena-playbook glass-panel" :open="defaultOpen">
    <summary class="playbook-summary">
      <span class="playbook-title">擂台玩法指南</span>
      <span class="playbook-sub">助威 · 动员 · 连击 · 应援榜</span>
    </summary>
    <div class="playbook-body">
      <div v-if="stats" class="stat-chips">
        <span v-if="(stats.today_cheerable ?? 0) > 0" class="chip hot">今日可助威 {{ stats.today_cheerable }} 场</span>
        <span v-if="(stats.spot_remaining ?? 0) > 0" class="chip">临场口号剩 {{ stats.spot_remaining }} 次</span>
        <span v-if="(stats.combo_opportunities ?? 0) > 0" class="chip combo">连击机会 {{ stats.combo_opportunities }}</span>
      </div>
      <ul class="playbook-list">
        <li><strong>任意队助威</strong> — 主队/副队 +10，中立助阵 +5，每场 1 次</li>
        <li><strong>冷门加成</strong> — 助威擂台战力落后方，额外 +3 军团贡献</li>
        <li><strong>竞猜+助威连击</strong> — 同场完成竞猜与助威，额外 +5 贡献</li>
        <li><strong>临场口号</strong> — 1 币/次，每日 3 次，任意今日参赛队 +2 贡献</li>
        <li><strong>比赛日动员</strong> — 主/副队各 20 币 +30，有机会掉落数字藏品</li>
      </ul>
      <div class="playbook-links">
        <button type="button" class="link-btn" @click="$router.push('/leaderboard?board=supporter')">
          查看球队应援榜 →
        </button>
        <button type="button" class="link-btn" @click="$router.push('/predict')">去竞猜大厅 →</button>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
defineProps<{
  stats?: {
    today_matches?: number
    today_cheerable?: number
    spot_remaining?: number
    combo_opportunities?: number
  } | null
  defaultOpen?: boolean
}>()
</script>

<style scoped>
.arena-playbook {
  padding: 0;
  margin-bottom: 16px;
  border-radius: 14px;
  overflow: hidden;
}

.playbook-summary {
  list-style: none;
  cursor: pointer;
  padding: 14px 18px;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 14px;
}

.playbook-summary::-webkit-details-marker {
  display: none;
}

.playbook-title {
  font-weight: 800;
  font-size: 0.95rem;
  color: #f0d9b5;
}

.playbook-sub {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.5);
}

.playbook-body {
  padding: 0 18px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}

.chip {
  font-size: 0.72rem;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.chip.hot {
  background: rgba(212, 165, 116, 0.15);
  border-color: rgba(212, 165, 116, 0.35);
  color: var(--wc-accent-gold);
}

.chip.combo {
  background: rgba(103, 194, 58, 0.12);
  border-color: rgba(103, 194, 58, 0.35);
  color: #b7eb8f;
}

.playbook-list {
  margin: 0 0 12px;
  padding-left: 18px;
  font-size: 0.82rem;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.72);
}

.playbook-list strong {
  color: rgba(255, 255, 255, 0.92);
}

.playbook-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.link-btn {
  padding: 0;
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.link-btn:hover {
  text-decoration: underline;
}
</style>
