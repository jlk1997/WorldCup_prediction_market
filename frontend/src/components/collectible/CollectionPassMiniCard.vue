<template>
  <router-link
    v-if="visible"
    to="/collection?tab=pass"
    class="pass-mini glass-panel"
    @click="onClick"
  >
    <div class="mini-ring" :class="{ claimable: (claimableCount ?? 0) > 0 }">
      <span class="mini-lv">{{ level }}</span>
    </div>
    <div class="mini-body">
      <div class="mini-head">
        <strong>藏品赛季手册</strong>
        <el-badge v-if="claimableCount" :value="claimableCount" type="success" />
      </div>
      <div class="mini-xp">
        <div class="mini-xp-fill" :style="{ width: `${xpPct}%` }" />
      </div>
      <p class="mini-sub">{{ subtitle }}</p>
    </div>
    <span class="mini-arrow">›</span>
  </router-link>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { authState } from '@/stores/authStore'
import { collectionPassNudge } from '@/stores/dailyStatusStore'
import { getCollectionPassSummaryLite, type CollectionPassSummaryLite } from '@/api/collectionPass'
import { trackEvent } from '@/utils/analytics'

const lite = ref<CollectionPassSummaryLite | null>(null)

const level = computed(() => lite.value?.level ?? collectionPassNudge.value?.level ?? 0)
const claimableCount = computed(
  () => lite.value?.claimable_count ?? collectionPassNudge.value?.claimable_count ?? 0,
)
const premiumUnlocked = computed(
  () => lite.value?.premium_unlocked ?? collectionPassNudge.value?.premium_unlocked ?? false,
)
const xpPct = computed(
  () => lite.value?.xp_level_progress_pct ?? collectionPassNudge.value?.xp_level_progress_pct ?? 0,
)
const xpToNext = computed(() => lite.value?.xp_to_next ?? collectionPassNudge.value?.xp_to_next ?? 0)
const nextLevel = computed(() => lite.value?.next_level ?? collectionPassNudge.value?.next_level ?? level.value + 1)

const visible = computed(() => authState.accessToken && level.value >= 0)

const subtitle = computed(() => {
  if (claimableCount.value) return `${claimableCount.value} 项奖励待领取`
  if (xpToNext.value) return `距 Lv.${nextLevel.value} 还差 ${xpToNext.value} XP`
  if (premiumUnlocked.value) return '尊享已解锁 · 满级'
  return '玩法升级 · 确定性奖励'
})

function onClick() {
  trackEvent('collection_pass_mini_click', { claimable: claimableCount.value })
}

async function loadLite() {
  if (!authState.accessToken) return
  try {
    lite.value = await getCollectionPassSummaryLite()
  } catch {
    /* nudge fallback */
  }
}

onMounted(loadLite)

watch(
  () => authState.accessToken,
  (token) => {
    if (token) void loadLite()
    else lite.value = null
  },
)
</script>

<style scoped>
.pass-mini {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.28);
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s, background 0.2s;
}

.pass-mini:hover {
  border-color: rgba(212, 165, 116, 0.5);
  background: rgba(212, 165, 116, 0.06);
}

.mini-ring {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid rgba(212, 165, 116, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-ring.claimable {
  border-color: #3dd68c;
  box-shadow: 0 0 12px rgba(61, 214, 140, 0.35);
}

.mini-lv {
  font-size: 1rem;
  font-weight: 800;
  color: var(--wc-gold);
}

.mini-body {
  flex: 1;
  min-width: 0;
}

.mini-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mini-head strong {
  font-size: 0.85rem;
  color: #f5f0e8;
}

.mini-xp {
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  margin-bottom: 4px;
}

.mini-xp-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--wc-gold), #7eb8ff);
  border-radius: 999px;
  transition: width 0.35s ease;
}

.mini-sub {
  margin: 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-arrow {
  flex-shrink: 0;
  font-size: 1.2rem;
  color: var(--wc-text-muted);
  opacity: 0.7;
}
</style>
