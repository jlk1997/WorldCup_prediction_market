<template>
  <div class="cheer-bar">
    <div class="side left" :class="{ leading: leftLeading }">
      <span class="name">{{ team1Name }}</span>
      <div class="track">
        <div class="fill" :style="{ width: pct1 + '%' }" />
      </div>
      <span class="count">{{ team1Cheers.toLocaleString() }}</span>
    </div>
    <div class="vs">VS</div>
    <div class="side right" :class="{ leading: rightLeading }">
      <span class="name">{{ team2Name }}</span>
      <div class="track">
        <div class="fill alt" :style="{ width: pct2 + '%' }" />
      </div>
      <span class="count">{{ team2Cheers.toLocaleString() }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  team1Name: string
  team2Name: string
  team1Cheers: number
  team2Cheers: number
}>()

const total = computed(() => props.team1Cheers + props.team2Cheers || 1)
const pct1 = computed(() => Math.round((props.team1Cheers / total.value) * 100))
const pct2 = computed(() => Math.round((props.team2Cheers / total.value) * 100))
const leftLeading = computed(() => props.team1Cheers >= props.team2Cheers && props.team1Cheers > 0)
const rightLeading = computed(() => props.team2Cheers > props.team1Cheers)
</script>

<style scoped>
.cheer-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 12px;
  align-items: center;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.side.leading .name {
  color: var(--wc-accent-gold);
}
.name {
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track {
  height: 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(90deg, var(--wc-accent-rose), var(--wc-accent-gold));
  transition: width 0.4s ease;
}
.fill.alt {
  background: linear-gradient(90deg, #5a7a9a, #8eb4d4);
}
.count {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  font-variant-numeric: tabular-nums;
}
.vs {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  font-weight: 700;
}
@media (max-width: 520px) {
  .cheer-bar {
    grid-template-columns: 1fr;
  }
  .vs { display: none; }
}
</style>
