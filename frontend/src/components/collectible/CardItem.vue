<template>
  <div
    class="card-item"
    :class="[`rarity-${card.rarity}`, { owned: card.owned !== false, dim: card.owned === false }]"
    @click="$emit('select', card)"
  >
    <div class="card-frame">
      <div v-if="card.image_url" class="card-image-wrap">
        <img :src="card.image_url" :alt="card.name" class="card-image" loading="lazy" />
      </div>
      <div v-else class="card-placeholder">
        <span class="placeholder-letter">{{ card.name.slice(0, 1) }}</span>
      </div>
      <div class="rarity-badge">{{ rarityLabel }}</div>
      <div v-if="(card.star ?? 0) > 1" class="star-badge">★{{ card.star }}</div>
      <div v-if="card.chain?.status === 'minted'" class="chain-badge" title="文昌链已铸造">链</div>
      <div v-else-if="card.chain?.status === 'minting' || card.chain?.status === 'pending'" class="chain-badge pending" title="上链中">⏳</div>
      <div v-if="card.highlights?.length" class="highlight-dot" title="已点亮高光印记" />
    </div>
    <p class="card-name">{{ card.name }}</p>
    <p v-if="card.owned === false" class="card-locked">未获得</p>
    <p v-else-if="(card.count ?? 0) > 1" class="card-count">×{{ card.count }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CollectibleCardBrief } from '@/api/collectible'
import { RARITY_LABELS } from '@/api/collectible'

const props = defineProps<{ card: CollectibleCardBrief }>()
defineEmits<{ select: [CollectibleCardBrief] }>()

const rarityLabel = computed(() => RARITY_LABELS[props.card.rarity] || props.card.rarity)
</script>

<style scoped>
.card-item {
  cursor: pointer;
  transition: transform 0.2s ease;
}
.card-item:hover {
  transform: translateY(-2px);
}
.card-frame {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(15, 18, 36, 0.95), rgba(25, 30, 55, 0.9));
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.card-item.rarity-rare .card-frame {
  border-color: rgba(126, 184, 255, 0.45);
  box-shadow: 0 0 12px rgba(126, 184, 255, 0.15);
}
.card-item.rarity-epic .card-frame {
  border-color: rgba(201, 120, 138, 0.5);
  box-shadow: 0 0 14px rgba(201, 120, 138, 0.2);
}
.card-item.rarity-legend .card-frame {
  border-color: rgba(232, 197, 71, 0.6);
  box-shadow: 0 0 18px rgba(232, 197, 71, 0.25);
}
.card-item.dim .card-frame {
  filter: grayscale(0.85) brightness(0.55);
  opacity: 0.75;
}
.card-image-wrap,
.card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.card-placeholder {
  background: radial-gradient(circle at 50% 30%, rgba(212, 165, 116, 0.15), transparent 70%);
}
.placeholder-letter {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--wc-gold, #d4a574);
}
.rarity-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  font-size: 0.62rem;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
}
.star-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 0.65rem;
  color: #e8c547;
}
.chain-badge {
  position: absolute;
  bottom: 6px;
  left: 6px;
  font-size: 0.58rem;
  padding: 1px 5px;
  border-radius: 999px;
  background: rgba(61, 214, 140, 0.25);
  color: #3dd68c;
  border: 1px solid rgba(61, 214, 140, 0.5);
}
.chain-badge.pending {
  background: rgba(232, 197, 71, 0.2);
  color: #e8c547;
  border-color: rgba(232, 197, 71, 0.45);
}
.highlight-dot {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3dd68c;
  box-shadow: 0 0 8px rgba(61, 214, 140, 0.8);
}
.card-name {
  margin: 6px 0 0;
  font-size: 0.78rem;
  text-align: center;
  color: var(--wc-text, #f0f4f8);
  line-height: 1.3;
}
.card-locked,
.card-count {
  margin: 2px 0 0;
  font-size: 0.65rem;
  text-align: center;
  color: var(--wc-text-muted, #9a94a8);
}
</style>
