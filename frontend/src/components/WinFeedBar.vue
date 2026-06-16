<template>
  <div
    v-if="show"
    class="win-feed-bar glass-panel"
    :class="{
      'above-bottom-nav': aboveBottomNav,
      pinned,
      compact: variant === 'compact',
    }"
  >
    <div class="feed-head">
      <span class="feed-label">
        <span class="pulse-dot" aria-hidden="true" />
        刚刚 {{ displayCount }} 人猜中
      </span>
      <button type="button" class="feed-join" @click="onJoin">我也去猜 →</button>
    </div>
    <div v-if="items.length" class="feed-track">
      <button
        v-for="(item, idx) in duplicated"
        :key="`${idx}-${item.nickname}-${item.team1}`"
        type="button"
        class="feed-item"
        @click="onJoin"
      >
        🎯 {{ item.nickname }} 猜中 {{ item.team1 }} vs {{ item.team2 }} +{{ item.points_awarded }} 分
      </button>
    </div>
    <p v-else class="feed-fallback">球友正在连猜连中 · 免费猜一场试试手气</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { WinFeedItem } from '@/api/commerce'
import { trackEvent } from '@/utils/analytics'

const props = withDefaults(
  defineProps<{
    items: WinFeedItem[]
    recentCount?: number
    aboveBottomNav?: boolean
    pinned?: boolean
    variant?: 'default' | 'compact'
    highlightMatchId?: number | null
  }>(),
  {
    recentCount: 0,
    aboveBottomNav: false,
    pinned: false,
    variant: 'default',
    highlightMatchId: null,
  },
)

const router = useRouter()

const show = computed(() => props.recentCount > 0 || props.items.length > 0)

const displayCount = computed(() => {
  if (props.recentCount > 0) return props.recentCount
  return props.items.length
})

const duplicated = computed(() => [...props.items, ...props.items])

function onJoin() {
  trackEvent('win_feed_click')
  const mid = props.highlightMatchId
  router.push(mid ? { path: '/predict', query: { highlight: String(mid) } } : '/predict')
}
</script>

<style scoped>
.win-feed-bar {
  margin-top: 12px;
  padding: 10px 14px;
  overflow: hidden;
  flex-shrink: 0;
}

.win-feed-bar.pinned {
  position: fixed;
  left: 16px;
  right: 16px;
  bottom: 72px;
  z-index: 20;
  margin-top: 0;
  opacity: 0.96;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.win-feed-bar.pinned.above-bottom-nav {
  bottom: calc(var(--wc-bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px) + 8px);
  margin-bottom: 0;
}

.win-feed-bar.above-bottom-nav:not(.pinned) {
  margin-bottom: calc(56px + env(safe-area-inset-bottom, 0px));
}

.feed-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.feed-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--wc-accent-gold, #d4a574);
  white-space: nowrap;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.5);
  animation: feed-pulse 1.8s ease infinite;
}

.feed-join {
  border: none;
  background: none;
  color: #8fd48a;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  white-space: nowrap;
}

.feed-join:hover {
  text-decoration: underline;
}

.feed-track {
  display: flex;
  gap: 32px;
  animation: win-feed-scroll 35s linear infinite;
  white-space: nowrap;
}

.compact .feed-track {
  gap: 24px;
  animation-duration: 40s;
}

.feed-item {
  border: none;
  background: none;
  font-size: 13px;
  color: var(--wc-text-muted, #9a94a8);
  cursor: pointer;
  padding: 0;
  transition: color 0.15s;
}

.feed-item:hover {
  color: #f5f0e8;
}

.feed-fallback {
  margin: 0;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}

@keyframes win-feed-scroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

@keyframes feed-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.45);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(103, 194, 58, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0);
  }
}
</style>
