<template>
  <div class="win-prob-chart">
    <svg viewBox="0 0 200 120" class="chart-svg">
      <polygon
        :points="trianglePoints"
        fill="rgba(210,167,109,0.15)"
        stroke="#D2A76D"
        stroke-width="1"
      />
      <text x="100" y="18" text-anchor="middle" class="lbl">{{ team1Label }}</text>
      <text x="35" y="105" text-anchor="middle" class="lbl">平</text>
      <text x="165" y="105" text-anchor="middle" class="lbl">{{ team2Label }}</text>
      <text x="100" y="55" text-anchor="middle" class="val">{{ pct.team1 }}%</text>
      <text x="45" y="85" text-anchor="middle" class="val">{{ pct.draw }}%</text>
      <text x="155" y="85" text-anchor="middle" class="val">{{ pct.team2 }}%</text>
    </svg>
    <div class="bars">
      <div class="bar-row"><span>主胜</span><div class="bar"><i :style="{ width: pct.team1 + '%' }" /></div></div>
      <div class="bar-row"><span>平局</span><div class="bar"><i :style="{ width: pct.draw + '%' }" /></div></div>
      <div class="bar-row"><span>客胜</span><div class="bar"><i :style="{ width: pct.team2 + '%' }" /></div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  team1?: string
  team2?: string
  winProbability: { team1: number; draw: number; team2: number }
}>()

const pct = computed(() => ({
  team1: Math.round(props.winProbability.team1 * 100),
  draw: Math.round(props.winProbability.draw * 100),
  team2: Math.round(props.winProbability.team2 * 100),
}))

const team1Label = computed(() => (props.team1 || '主').slice(0, 4))
const team2Label = computed(() => (props.team2 || '客').slice(0, 4))

const trianglePoints = computed(() => {
  const t1 = pct.value.team1 / 100
  const dr = pct.value.draw / 100
  const t2 = pct.value.team2 / 100
  const top = { x: 100, y: 25 + (1 - t1) * 20 }
  const left = { x: 40 + (1 - dr) * 15, y: 95 }
  const right = { x: 160 - (1 - t2) * 15, y: 95 }
  return `${top.x},${top.y} ${left.x},${left.y} ${right.x},${right.y}`
})
</script>

<style scoped>
.win-prob-chart { display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }
.chart-svg { width: 200px; height: 120px; }
.lbl { fill: #A0A0A0; font-size: 10px; }
.val { fill: #D2A76D; font-size: 11px; font-weight: bold; }
.bars { flex: 1; min-width: 160px; display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: #A0A0A0; }
.bar-row span { width: 36px; }
.bar { flex: 1; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; }
.bar i { display: block; height: 100%; background: linear-gradient(90deg, #A67C41, #D2A76D); }
</style>
