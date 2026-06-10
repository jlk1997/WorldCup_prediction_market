<template>
  <div ref="rootEl" class="virtual-list" @scroll="onScroll">
    <div class="virtual-spacer" :style="{ height: `${totalHeight}px` }">
      <div class="virtual-window" :style="{ transform: `translateY(${offsetY}px)` }">
        <div
          v-for="item in visibleItems"
          :key="keyOf(item.data, item.index)"
          class="virtual-item"
          :style="{ height: `${itemHeight}px` }"
        >
          <slot :item="item.data" :index="item.index" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    items: T[]
    itemHeight: number
    overscan?: number
    itemKey?: (item: T, index: number) => string | number
    scrollToIndex?: number | null
  }>(),
  {
    overscan: 3,
    scrollToIndex: null,
  },
)

const rootEl = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const viewportHeight = ref(400)

function keyOf(item: T, index: number) {
  return props.itemKey ? props.itemKey(item, index) : index
}

const totalHeight = computed(() => props.items.length * props.itemHeight)

const startIndex = computed(() =>
  Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.overscan),
)

const endIndex = computed(() => {
  const visible = Math.ceil(viewportHeight.value / props.itemHeight) + props.overscan * 2
  return Math.min(props.items.length, startIndex.value + visible)
})

const offsetY = computed(() => startIndex.value * props.itemHeight)

const visibleItems = computed(() =>
  props.items.slice(startIndex.value, endIndex.value).map((data, i) => ({
    data,
    index: startIndex.value + i,
  })),
)

function onScroll() {
  if (!rootEl.value) return
  scrollTop.value = rootEl.value.scrollTop
}

function measure() {
  if (rootEl.value) viewportHeight.value = rootEl.value.clientHeight || 400
}

function scrollToItem(index: number) {
  if (!rootEl.value || index < 0) return
  rootEl.value.scrollTop = index * props.itemHeight
  scrollTop.value = rootEl.value.scrollTop
}

onMounted(() => {
  measure()
  window.addEventListener('resize', measure)
})

onUnmounted(() => {
  window.removeEventListener('resize', measure)
})

watch(
  () => props.scrollToIndex,
  (idx) => {
    if (idx != null && idx >= 0) scrollToItem(idx)
  },
  { immediate: true },
)

defineExpose({ scrollToItem })
</script>

<style scoped>
.virtual-list {
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
  -webkit-overflow-scrolling: touch;
}
.virtual-spacer {
  position: relative;
  width: 100%;
}
.virtual-window {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
}
.virtual-item {
  box-sizing: border-box;
  overflow: hidden;
}
</style>
