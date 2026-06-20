<template>
  <aside class="lineup-column" :class="{ 'is-main': tagClass === 'main', 'lineup-column--drawer': inDrawer }">
    <div class="team-header glass-panel" @click="$emit('header-click')">
      <span class="side-tag-inline" :class="tagClass">{{ tagLabel }}</span>
      <h2 class="team-name">{{ teamName }}</h2>
      <div class="team-info-blocks" v-if="!loading && data">
        <div class="info-block" v-if="hasValue(data.fifa_ranking)">
          <span class="block-label">FIFA</span>
          <strong class="block-value highlight">{{ data.fifa_ranking }}</strong>
        </div>
        <div class="info-block" v-if="hasValue(data.total_value)">
          <span class="block-label">总身价</span>
          <strong class="block-value highlight">{{ data.total_value }}</strong>
        </div>
        <div class="info-block" v-if="hasValue(data.coach)">
          <span class="block-label">主帅</span>
          <strong class="block-value">{{ data.coach }}</strong>
        </div>
        <div class="info-block" v-if="hasValue(data.formation)">
          <span class="block-label">阵型</span>
          <strong class="block-value">{{ data.formation }}</strong>
        </div>
      </div>
      <div v-else-if="loading" class="team-info-blocks">
        <div class="info-block"><span class="block-label">阵容</span><strong class="block-value">加载中…</strong></div>
      </div>
    </div>

    <div class="data-stack">
      <div class="data-card key-player glass-panel" v-if="topPlayer">
        <div class="card-header">
          <h3>核心球员</h3>
          <p>STAR PLAYER</p>
        </div>
        <div class="card-body">
          <div class="kp-header">
            <span class="kp-name">{{ topPlayer.name }}</span>
            <span class="kp-rating" :class="ratingClass(topPlayer.overall_rating)">{{ topPlayer.overall_rating }}</span>
          </div>
        </div>
      </div>

      <div class="data-card starting-xi glass-panel" v-if="lineup.length">
        <div class="card-header">
          <h3>预计首发</h3>
          <p>{{ lineup.length }} 人 · 按位置/能力排序</p>
        </div>
        <div class="card-body player-list">
          <div class="player-item" v-for="player in lineup" :key="`${teamName}-${player.name}`">
            <div class="p-pos" :class="posClass(player.position)">{{ player.position || '-' }}</div>
            <div class="p-info">
              <div class="p-name">
                {{ player.name }}
                <span class="p-club" v-if="player.club">({{ player.club }})</span>
                <span v-if="player.is_starter" class="starter-badge">首发</span>
              </div>
              <div class="p-meta">
                <span v-if="player.age">{{ player.age }}岁</span>
                <span v-if="player.overall_rating"> · 能力 {{ player.overall_rating }}</span>
              </div>
            </div>
            <div class="p-rating" :class="ratingClass(player.overall_rating)">{{ player.overall_rating || '-' }}</div>
          </div>
        </div>
      </div>

      <div class="data-card bench glass-panel" v-if="bench.length">
        <div class="card-header">
          <h3>替补席</h3>
          <p>{{ bench.length }} 人</p>
        </div>
        <div class="card-body player-list player-list--compact">
          <div class="player-item" v-for="player in bench" :key="`${teamName}-b-${player.name}`">
            <div class="p-pos" :class="posClass(player.position)">{{ player.position || '-' }}</div>
            <div class="p-info">
              <div class="p-name">{{ player.name }}</div>
            </div>
            <div class="p-rating" :class="ratingClass(player.overall_rating)">{{ player.overall_rating || '-' }}</div>
          </div>
        </div>
      </div>

      <div class="data-card glass-panel" v-if="!loading && !data">
        <div class="card-body empty-data">暂无 {{ teamName }} 球员数据</div>
      </div>
      <div class="data-card glass-panel" v-else-if="!loading && data && !lineup.length && !bench.length">
        <div class="card-body empty-data">该队暂无球员档案</div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
export type LineupPlayer = {
  name: string
  position?: string
  overall_rating?: number
  club?: string
  age?: number
  is_starter?: boolean
}

defineProps<{
  teamName: string
  tagLabel: string
  tagClass: string
  data: Record<string, unknown> | null
  loading: boolean
  topPlayer: LineupPlayer | null
  lineup: LineupPlayer[]
  bench: LineupPlayer[]
  inDrawer?: boolean
}>()

defineEmits<{ 'header-click': [] }>()

function hasValue(v: unknown) {
  if (v == null || v === '') return false
  return String(v).trim() !== '待定'
}

function posClass(pos?: string) {
  if (pos === '门将') return 'pos-gk'
  if (pos === '后卫') return 'pos-df'
  if (pos === '中场') return 'pos-mf'
  if (pos === '前锋') return 'pos-fw'
  return ''
}

function ratingClass(rating?: number) {
  if (!rating) return 'rating-gray'
  if (rating >= 80) return 'rating-gold'
  if (rating >= 70) return 'rating-silver'
  return 'rating-bronze'
}
</script>

<style scoped>
.lineup-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: auto;
  max-height: calc(var(--app-height, 100dvh) - 240px);
  min-width: 0;
}

.lineup-column.is-main .team-header {
  border: 1px solid rgba(212, 165, 116, 0.35);
  box-shadow: 0 0 16px rgba(212, 165, 116, 0.12);
}

.team-header {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(10, 12, 18, 0.72) !important;
  backdrop-filter: blur(10px);
  cursor: pointer;
}

.team-name {
  font-size: 1.35rem;
  font-weight: 800;
  margin: 0 0 8px;
  color: #fff;
}

.side-tag-inline {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  margin-bottom: 6px;
}

.side-tag-inline.home,
.side-tag-inline.main {
  color: #d2a76d;
  background: rgba(210, 167, 109, 0.12);
  border: 1px solid rgba(210, 167, 109, 0.3);
}

.side-tag-inline.main {
  color: #ffe8b8;
  background: rgba(212, 165, 116, 0.22);
  border-color: rgba(212, 165, 116, 0.55);
}

.side-tag-inline.away {
  color: #c9d1d9;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.team-info-blocks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info-block {
  background: rgba(30, 26, 23, 0.4);
  border: 1px solid rgba(210, 167, 109, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 64px;
}

.info-block .block-label {
  color: #a0a0a0;
  font-size: 0.62rem;
}

.info-block .block-value {
  color: #fff;
  font-size: 0.85rem;
  font-weight: bold;
}

.info-block .block-value.highlight {
  color: #d2a76d;
}

.data-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.data-card {
  background: rgba(10, 12, 18, 0.65);
  border-radius: 10px;
  padding: 10px 12px;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.starting-xi,
.bench {
  flex: 1;
  max-height: 320px;
}

.bench {
  max-height: 180px;
}

.card-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 6px;
  margin-bottom: 8px;
  text-align: center;
  flex-shrink: 0;
}

.card-header h3 {
  margin: 0;
  font-size: 0.85rem;
  color: #d2a76d;
}

.card-header p {
  margin: 2px 0 0;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.45);
}

.kp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kp-name {
  font-weight: 800;
  font-size: 1rem;
  color: #fff;
}

.kp-rating {
  font-size: 1.2rem;
  font-weight: 900;
  color: #d2a76d;
}

.player-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  padding-right: 4px;
  flex: 1;
}

.player-list--compact .player-item {
  padding-bottom: 4px;
}

.player-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 6px;
  border-bottom: 1px dashed rgba(210, 167, 109, 0.12);
}

.player-item:last-child {
  border-bottom: none;
}

.p-pos {
  font-size: 0.68rem;
  padding: 2px 5px;
  border-radius: 4px;
  min-width: 32px;
  text-align: center;
  font-weight: bold;
  flex-shrink: 0;
}

.pos-gk { color: #a0a0a0; border: 1px solid #a0a0a0; }
.pos-df, .pos-mf, .pos-fw { color: #d2a76d; border: 1px solid rgba(210, 167, 109, 0.4); }

.p-info {
  flex: 1;
  min-width: 0;
}

.p-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.p-club {
  font-size: 0.72rem;
  color: #a0a0a0;
  margin-left: 4px;
}

.starter-badge {
  font-size: 0.58rem;
  background: rgba(210, 167, 109, 0.15);
  color: #d2a76d;
  border: 1px solid rgba(210, 167, 109, 0.35);
  padding: 0 4px;
  border-radius: 3px;
  margin-left: 4px;
}

.p-meta {
  font-size: 0.65rem;
  color: #9aa0a8;
}

.p-rating {
  font-weight: 900;
  font-size: 0.95rem;
  flex-shrink: 0;
}

.rating-gold { color: #d2a76d; }
.rating-silver { color: #a67c41; }
.rating-bronze { color: #8a6327; }
.rating-gray { color: #a0a0a0; }

.empty-data {
  text-align: center;
  color: #a0a0a0;
  padding: 16px 0;
  font-size: 0.85rem;
}

.lineup-column--drawer .team-name {
  font-size: 1.15rem;
}

.lineup-column--drawer .p-name {
  white-space: normal;
  line-height: 1.3;
}

.lineup-column--drawer .player-item {
  min-height: 44px;
}

@media (max-width: 768px) {
  .lineup-column {
    max-height: none;
  }
  .starting-xi,
  .bench {
    max-height: 280px;
  }
}
</style>
