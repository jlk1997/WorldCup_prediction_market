<template>
  <div class="sparkline">
    <svg v-if="points.length > 1" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none" class="spark-svg">
      <polyline :points="polyline" fill="none" :stroke="strokeColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
      <polygon :points="areaPolygon" :fill="`url(#spark-grad)`" opacity="0.18" />
      <defs>
        <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="strokeColor" />
          <stop offset="100%" stop-color="transparent" />
        </linearGradient>
      </defs>
    </svg>
    <div v-else class="spark-empty">暂无成交数据</div>
    <div class="spark-meta">
      <span>历史成交（可用积分）</span>
      <span class="muted">仅供收藏体验，无现金价值</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ points: number[] }>()

const width = 300
const height = 64

const strokeColor = computed(() => {
  if (props.points.length < 2) return '#d4a574'
  return props.points[props.points.length - 1] >= props.points[0] ? '#5fc88f' : '#e07a7a'
})

function scaled(): { x: number; y: number }[] {
  const pts = props.points
  if (pts.length < 2) return []
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const range = max - min || 1
  return pts.map((p, i) => ({
    x: (i / (pts.length - 1)) * width,
    y: height - 6 - ((p - min) / range) * (height - 12),
  }))
}

const polyline = computed(() => scaled().map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '))
const areaPolygon = computed(() => {
  const s = scaled()
  if (!s.length) return ''
  return `0,${height} ` + s.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + ` ${width},${height}`
})
</script>

<style scoped>
.sparkline {
  border-radius: 8px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.03);
}
.spark-svg {
  width: 100%;
  height: 64px;
  display: block;
}
.spark-empty {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.spark-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 0.62rem;
  color: var(--wc-text-secondary);
}
.spark-meta .muted {
  color: var(--wc-text-muted);
}
</style>
