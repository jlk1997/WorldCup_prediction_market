<template>
  <div class="album-grid-wrap">
    <div class="album-grid">
      <CardItem
        v-for="card in cards"
        :key="card.code"
        :card="card"
        @select="$emit('select', $event)"
      />
    </div>
    <div ref="sentinelRef" class="load-sentinel" aria-hidden="true" />
    <div v-if="loadingMore" class="load-more-hint">加载中…</div>
    <div v-else-if="hasMore" class="load-more-hint muted">继续下滑加载更多</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import CardItem from './CardItem.vue'
import type { CollectibleCardBrief } from '@/api/collectible'

const props = withDefaults(
  defineProps<{
    cards: CollectibleCardBrief[]
    hasMore?: boolean
    loadingMore?: boolean
  }>(),
  {
    hasMore: false,
    loadingMore: false,
  },
)

const emit = defineEmits<{ select: [CollectibleCardBrief]; loadMore: [] }>()

const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

function setupObserver() {
  observer?.disconnect()
  if (!sentinelRef.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (!props.hasMore || props.loadingMore) return
      if (entries.some((e) => e.isIntersecting)) emit('loadMore')
    },
    { root: null, rootMargin: '240px 0px', threshold: 0 },
  )
  observer.observe(sentinelRef.value)
}

onMounted(() => {
  setupObserver()
})

onUnmounted(() => {
  observer?.disconnect()
})

watch(
  () => [props.hasMore, props.loadingMore, props.cards.length] as const,
  () => setupObserver(),
)
</script>

<style scoped>
.album-grid-wrap {
  width: 100%;
}

.album-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px 14px;
  padding: 6px 4px 8px;
}

@media (min-width: 480px) {
  .album-grid {
    gap: 18px 16px;
    padding: 8px 6px 12px;
  }
}

@media (min-width: 768px) {
  .album-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 20px 18px;
  }
}

@media (min-width: 960px) {
  .album-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

.load-sentinel {
  height: 1px;
  width: 100%;
  pointer-events: none;
}

.load-more-hint {
  text-align: center;
  font-size: 0.75rem;
  color: var(--wc-gold);
  padding: 12px 0 6px;
}

.load-more-hint.muted {
  color: var(--wc-text-muted);
}
</style>
