<template>
  <div class="asset-hub" :class="{ compact }">
    <div v-if="showBalance && summary" class="hub-balance glass-inner">
      <div class="hb-item">
        <span class="hb-label">可用积分</span>
        <strong class="hb-val">{{ summary.redeem_points.toLocaleString() }}</strong>
      </div>
      <div class="hb-divider" />
      <div class="hb-item">
        <span class="hb-label">组合估值</span>
        <strong class="hb-val gold">{{ summary.portfolio_value.toLocaleString() }}</strong>
      </div>
    </div>

    <nav class="hub-nav" aria-label="数字资产导航">
      <router-link
        v-for="tile in tiles"
        :key="tile.to"
        :to="tile.to"
        class="hub-tile glass-inner"
        :class="{ active: isActive(tile.to) }"
      >
        <span class="tile-icon" aria-hidden="true">{{ tile.icon }}</span>
        <span class="tile-label">{{ tile.label }}</span>
        <span v-if="tile.badge" class="tile-badge">{{ tile.badge > 99 ? '99+' : tile.badge }}</span>
        <span v-else-if="tile.hint" class="tile-hint">{{ tile.hint }}</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAssetHubSummary, type AssetHubSummary } from '@/api/asset'
import { authState } from '@/stores/authStore'

const props = withDefaults(
  defineProps<{
    compact?: boolean
    showBalance?: boolean
    /** 挂载后自动拉取；设为 false 时由父组件调用 refresh() */
    autoFetch?: boolean
  }>(),
  { compact: false, showBalance: true, autoFetch: true },
)

const emit = defineEmits<{ loaded: [AssetHubSummary | null] }>()

const route = useRoute()
const summary = ref<AssetHubSummary | null>(null)
const loading = ref(false)

const tiles = computed(() => {
  const s = summary.value
  return [
    {
      to: '/market',
      label: '交易行',
      icon: '🏪',
      badge: 0,
      hint: '买卖',
    },
    {
      to: '/mint',
      label: '首发打新',
      icon: '✨',
      badge: s?.live_mint_events || 0,
      hint: s?.live_mint_events ? undefined : '限量',
    },
    {
      to: '/fantasy',
      label: '数字阵容',
      icon: '⚽',
      badge: 0,
      hint: s?.fantasy_rank ? `#${s.fantasy_rank}` : s?.fantasy_score ? `${s.fantasy_score}分` : '周榜',
    },
    {
      to: '/me/assets',
      label: '我的资产',
      icon: '💎',
      badge: actionBadge(s),
      hint: actionBadge(s) ? undefined : '管理',
    },
  ]
})

function actionBadge(s: AssetHubSummary | null | undefined): number {
  if (!s) return 0
  let n = 0
  if (s.claimable_stake_points > 0) n += 1
  if (s.duel_pending_incoming > 0) n += s.duel_pending_incoming
  if (s.duel_pending_outgoing > 0) n += 1
  return n
}

function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}

async function refresh() {
  if (!authState.accessToken) {
    summary.value = null
    emit('loaded', null)
    return
  }
  loading.value = true
  try {
    summary.value = await getAssetHubSummary()
    emit('loaded', summary.value)
  } catch {
    summary.value = null
    emit('loaded', null)
  } finally {
    loading.value = false
  }
}

function onVisibility() {
  if (document.visibilityState === 'visible' && props.autoFetch) refresh()
}

watch(
  () => authState.accessToken,
  () => {
    if (props.autoFetch) refresh()
  },
)

onMounted(() => {
  if (props.autoFetch) refresh()
  document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibility)
})

defineExpose({ refresh, summary, loading })
</script>

<style scoped>
.asset-hub {
  margin-bottom: 14px;
}
.hub-balance {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 10px 14px;
  border-radius: 12px;
  margin-bottom: 10px;
}
.hb-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.hb-label {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.hb-val {
  font-size: 1.05rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--wc-text-secondary);
}
.hb-val.gold {
  color: var(--wc-accent-gold);
}
.hb-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.08);
}
.hub-nav {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.compact .hub-nav {
  gap: 6px;
}
.hub-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 6px;
  border-radius: 12px;
  text-decoration: none;
  color: var(--wc-text-secondary);
  transition: transform 0.15s, background 0.15s;
  min-height: 64px;
}
.compact .hub-tile {
  min-height: 56px;
  padding: 8px 4px;
}
.hub-tile:active {
  transform: scale(0.97);
}
.hub-tile.active {
  outline: 1px solid rgba(232, 200, 138, 0.35);
  background: rgba(232, 200, 138, 0.06);
}
.tile-icon {
  font-size: 1.15rem;
  line-height: 1;
}
.compact .tile-icon {
  font-size: 1rem;
}
.tile-label {
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}
.compact .tile-label {
  font-size: 0.66rem;
}
.tile-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #e85d5d;
  color: #fff;
  font-size: 0.58rem;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.tile-hint {
  font-size: 0.58rem;
  color: var(--wc-text-muted);
  margin-top: -2px;
}
</style>
