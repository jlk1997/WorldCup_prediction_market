<template>
  <div class="synth-panel glass-panel">
    <h3>碎片合成</h3>
    <p class="hint">消耗碎片 + 可用积分合成指定卡牌（传奇卡不可合成）</p>
    <div class="shard-bar">
      <span v-for="r in rarities" :key="r" class="shard-chip">
        {{ RARITY_LABELS[r] }} {{ shards[r] ?? 0 }}
      </span>
      <span class="shard-chip pts">可用分 {{ redeemPoints }}</span>
    </div>
    <div v-if="!options.length" class="empty">暂无可合成卡牌，继续猜中收集碎片吧</div>
    <div v-else class="options">
      <div v-for="opt in options" :key="opt.code" class="option-row">
        <div class="opt-info">
          <strong>{{ opt.name }}</strong>
          <span class="cost">
            {{ opt.cost.shards }} 碎片 · {{ opt.cost.redeem_points }} 可用分
          </span>
        </div>
        <el-button
          size="small"
          type="primary"
          :disabled="!opt.can_synthesize"
          :loading="loadingCode === opt.code"
          @click="$emit('synthesize', opt.code)"
        >
          合成
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CardRarity, SynthesisOption } from '@/api/collectible'
import { RARITY_LABELS } from '@/api/collectible'

defineProps<{
  options: SynthesisOption[]
  shards: Record<string, number>
  redeemPoints: number
  loadingCode?: string | null
}>()

defineEmits<{ synthesize: [string] }>()

const rarities: CardRarity[] = ['common', 'rare', 'epic', 'legend']
</script>

<style scoped>
.synth-panel {
  padding: 16px;
  border-radius: 12px;
}
.synth-panel h3 {
  margin: 0 0 6px;
}
.hint {
  margin: 0 0 12px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}
.shard-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.shard-chip {
  font-size: 0.72rem;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(212, 165, 116, 0.25);
}
.shard-chip.pts {
  border-color: rgba(61, 214, 140, 0.35);
}
.empty {
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 280px;
  overflow-y: auto;
}
.option-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.opt-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.opt-info strong {
  font-size: 0.85rem;
}
.cost {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
</style>
