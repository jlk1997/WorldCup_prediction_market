<template>
  <div class="player-radar" v-if="entries.length">
    <svg :viewBox="`0 0 ${size} ${size}`" class="radar-svg">
      <polygon
        v-for="level in [0.25, 0.5, 0.75, 1]"
        :key="level"
        :points="gridPoints(level)"
        fill="none"
        stroke="rgba(210,167,109,0.2)"
        stroke-width="0.5"
      />
      <polygon :points="valuePoints" fill="rgba(210,167,109,0.35)" stroke="#D2A76D" stroke-width="1.5" />
      <text
        v-for="(e, i) in entries"
        :key="e.key"
        :x="labelPos(i).x"
        :y="labelPos(i).y"
        text-anchor="middle"
        class="radar-label"
      >{{ e.key }}</text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ stats: Record<string, number> }>()
const size = 220
const cx = size / 2
const cy = size / 2
const radius = 80

const entries = computed(() =>
  Object.entries(props.stats || {})
    .filter(([, v]) => typeof v === 'number')
    .slice(0, 6)
    .map(([key, value]) => ({ key, value: Math.min(100, Math.max(0, value)) }))
)

function angle(i: number) {
  return (Math.PI * 2 * i) / entries.value.length - Math.PI / 2
}

function gridPoints(level: number) {
  return entries.value
    .map((_, i) => {
      const r = radius * level
      return `${cx + r * Math.cos(angle(i))},${cy + r * Math.sin(angle(i))}`
    })
    .join(' ')
}

const valuePoints = computed(() =>
  entries.value
    .map((e, i) => {
      const r = (e.value / 100) * radius
      return `${cx + r * Math.cos(angle(i))},${cy + r * Math.sin(angle(i))}`
    })
    .join(' ')
)

function labelPos(i: number) {
  const r = radius + 16
  return { x: cx + r * Math.cos(angle(i)), y: cy + r * Math.sin(angle(i)) + 4 }
}
</script>

<style scoped>
.player-radar { display: flex; justify-content: center; }
.radar-svg { width: 220px; height: 220px; }
.radar-label { fill: #A0A0A0; font-size: 9px; }
</style>
