<template>
  <div class="asset-summary">
    <div class="core-row">
      <button type="button" class="asset-cell" @click="$router.push('/shop')">
        <span class="asset-label">球迷币</span>
        <span class="asset-value gold">{{ user?.fan_coins ?? 0 }}</span>
      </button>
      <button
        type="button"
        class="asset-cell highlight"
        @click="$router.push({ path: '/shop', query: { tab: 'redeem' } })"
      >
        <span class="asset-label">可用积分</span>
        <span class="asset-value rose">{{ user?.redeem_points ?? 0 }}</span>
      </button>
      <button type="button" class="asset-cell" @click="$router.push('/leaderboard')">
        <span class="asset-label">累计积分</span>
        <span class="asset-value">{{ user?.season_points ?? 0 }}</span>
      </button>
    </div>

    <button type="button" class="more-toggle" @click="expanded = !expanded">
      {{ expanded ? '收起更多数据' : '更多数据' }}
      <span class="toggle-arrow" :class="{ open: expanded }">›</span>
    </button>

    <div v-if="expanded" class="extra-row">
      <div class="extra-cell">
        <span class="asset-label">军团贡献</span>
        <span class="asset-value sm">{{ user?.battalion_points_season ?? 0 }}</span>
      </div>
      <div v-if="(user?.extra_free_predict_daily ?? 0) > 0" class="extra-cell">
        <span class="asset-label">额外竞猜</span>
        <span class="asset-value sm">+{{ user?.extra_free_predict_daily }}/日</span>
      </div>
      <div class="extra-cell">
        <span class="asset-label">连胜</span>
        <span class="asset-value sm">{{ user?.win_streak ?? 0 }}</span>
      </div>
      <button type="button" class="extra-cell link" @click="$router.push('/me/assets')">
        <span class="asset-label">球星卡资产</span>
        <span class="asset-value sm gold">查看 →</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { AuthUser } from '../../stores/authStore'

defineProps<{
  user: AuthUser | null
}>()

const expanded = ref(false)
</script>

<style scoped>
.asset-summary {
  margin-bottom: 12px;
}

.core-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.asset-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(12, 14, 28, 0.55);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.asset-cell:hover {
  border-color: rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.08);
}

.asset-cell.highlight {
  border-color: rgba(201, 120, 138, 0.35);
  background: rgba(201, 120, 138, 0.08);
}

.asset-label {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
}

.asset-value {
  font-size: 1.35rem;
  font-weight: 800;
  color: #f5f0e8;
  line-height: 1.1;
}

.asset-value.sm {
  font-size: 1.1rem;
}

.asset-value.gold {
  color: var(--wc-accent-gold);
}

.asset-value.rose {
  color: var(--wc-accent-rose);
}

.more-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  margin-top: 8px;
  padding: 6px;
  border: none;
  background: none;
  color: var(--wc-text-muted);
  font-size: 0.75rem;
  cursor: pointer;
}

.toggle-arrow {
  display: inline-block;
  transition: transform 0.2s;
  transform: rotate(90deg);
}

.toggle-arrow.open {
  transform: rotate(-90deg);
}

.extra-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.extra-cell {
  flex: 1;
  min-width: 90px;
  text-align: center;
}
.extra-cell.link {
  border: none;
  background: rgba(212, 165, 116, 0.08);
  border-radius: 8px;
  cursor: pointer;
}
.extra-cell.link:hover {
  background: rgba(212, 165, 116, 0.15);
}
</style>
