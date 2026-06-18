<template>
  <VirtualList
    class="album-virtual-list"
    :items="rows"
    :item-height="rowHeight"
    :item-key="rowKey"
    @scroll="onScroll"
  >
    <template #default="{ item: row }">
      <div class="album-row" :style="{ gridTemplateColumns: `repeat(${columns}, 1fr)` }">
        <CardItem
          v-for="card in row"
          :key="card.code"
          :card="card"
          @select="$emit('select', $event)"
        />
      </div>
    </template>
  </VirtualList>
  <div v-if="loadingMore" class="load-more-hint">加载中…</div>
  <div v-else-if="hasMore" class="load-more-hint muted">继续下滑加载更多</div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import VirtualList from '@/components/VirtualList.vue'
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

const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 360)

const columns = computed(() => {
  const w = viewportWidth.value
  if (w >= 960) return 5
  if (w >= 768) return 4
  return 3
})

const rowHeight = computed(() => (columns.value >= 4 ? 168 : 148))

const rows = computed(() => {
  const out: CollectibleCardBrief[][] = []
  const cols = columns.value
  for (let i = 0; i < props.cards.length; i += cols) {
    out.push(props.cards.slice(i, i + cols))
  }
  return out
})

function rowKey(row: CollectibleCardBrief[]) {
  return row[0]?.code ?? 'empty'
}

function onScroll(el: HTMLElement) {
  if (!props.hasMore || props.loadingMore) return
  const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - rowHeight.value * 2
  if (nearBottom) emit('loadMore')
}

function onResize() {
  viewportWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.album-virtual-list {
  max-height: min(72vh, 720px);
  min-height: 320px;
}
.album-row {
  display: grid;
  gap: 12px;
  padding-bottom: 12px;
  box-sizing: border-box;
}
.load-more-hint {
  text-align: center;
  font-size: 0.75rem;
  color: var(--wc-gold);
  padding: 10px 0 4px;
}
.load-more-hint.muted {
  color: var(--wc-text-muted);
}
</style>
