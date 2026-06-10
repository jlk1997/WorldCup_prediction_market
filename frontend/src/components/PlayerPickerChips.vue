<template>
  <div class="player-picker">
    <p class="hint">最多选 3 名（{{ modelValue.length }}/3）</p>
    <div class="chips">
      <button
        v-for="p in players"
        :key="p.id"
        type="button"
        class="chip"
        :class="{ on: modelValue.includes(p.id) }"
        @click="toggle(p.id)"
      >
        {{ p.name }}
        <span v-if="p.is_starter" class="star">★</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PlayerBrief } from '../api/profile'

const props = defineProps<{ players: PlayerBrief[]; modelValue: number[] }>()
const emit = defineEmits<{ 'update:modelValue': [number[]] }>()

function toggle(id: number) {
  let next = [...props.modelValue]
  if (next.includes(id)) {
    next = next.filter((x) => x !== id)
  } else if (next.length < 3) {
    next.push(id)
  }
  emit('update:modelValue', next)
}
</script>

<style scoped>
.hint { font-size: 0.85rem; color: var(--wc-text-muted); margin-bottom: 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  padding: 8px 14px;
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.15);
  background: transparent;
  color: var(--wc-text-primary);
  cursor: pointer;
}
.chip.on {
  border-color: var(--wc-accent-rose);
  background: rgba(201,120,138,0.2);
}
.star { color: var(--wc-accent-gold); margin-left: 4px; }
</style>
