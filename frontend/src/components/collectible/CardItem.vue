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
      <div
        v-else-if="card.chain?.status === 'minting' || card.chain?.status === 'pending'"
        class="chain-badge pending"
        title="上链中"
      >
        ⏳
      </div>
      <div v-if="card.highlights?.length" class="highlight-dot" title="已点亮高光印记" />

      <div class="card-name-overlay">
        <p class="card-name-text" :title="card.name">{{ card.name }}</p>
        <p v-if="card.owned === false" class="card-status locked">未获得</p>
        <p v-else-if="(card.count ?? 0) > 1" class="card-status owned-count">×{{ card.count }}</p>
      </div>
    </div>
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
  transition: transform 0.22s ease, filter 0.22s ease;
  min-width: 0;
}

.card-item:hover {
  transform: translateY(-3px);
}

.card-item:active {
  transform: scale(0.98);
}

.card-frame {
  position: relative;
  aspect-ratio: 3 / 4.1;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(155deg, rgba(18, 22, 42, 0.98), rgba(28, 34, 62, 0.92));
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
}

.card-item.rarity-common .card-frame {
  border-color: rgba(158, 176, 200, 0.35);
}

.card-item.rarity-rare .card-frame {
  border-color: rgba(126, 184, 255, 0.5);
  box-shadow: 0 4px 16px rgba(126, 184, 255, 0.18);
}

.card-item.rarity-epic .card-frame {
  border-color: rgba(201, 120, 138, 0.55);
  box-shadow: 0 4px 18px rgba(201, 120, 138, 0.22);
}

.card-item.rarity-legend .card-frame {
  border-color: rgba(232, 197, 71, 0.65);
  box-shadow: 0 6px 22px rgba(232, 197, 71, 0.28);
}

.card-item.dim .card-frame {
  filter: grayscale(0.75) brightness(0.62);
}

.card-item.dim .card-name-overlay {
  opacity: 0.88;
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
  background: radial-gradient(circle at 50% 28%, rgba(212, 165, 116, 0.18), transparent 72%);
}

.placeholder-letter {
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--wc-gold, #d4a574);
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.45);
}

.rarity-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 0.62rem;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(8, 10, 20, 0.72);
  color: #fff;
  font-weight: 600;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.card-item.rarity-legend .rarity-badge {
  color: #ffe9a8;
  border-color: rgba(232, 197, 71, 0.45);
}

.star-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 0.68rem;
  font-weight: 700;
  color: #ffe566;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
}

.chain-badge {
  position: absolute;
  bottom: 52px;
  left: 8px;
  font-size: 0.58rem;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(61, 214, 140, 0.28);
  color: #3dd68c;
  border: 1px solid rgba(61, 214, 140, 0.5);
}

.chain-badge.pending {
  background: rgba(232, 197, 71, 0.22);
  color: #e8c547;
  border-color: rgba(232, 197, 71, 0.45);
}

.highlight-dot {
  position: absolute;
  bottom: 54px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3dd68c;
  box-shadow: 0 0 8px rgba(61, 214, 140, 0.8);
}

.card-name-overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 28px 8px 8px;
  background: linear-gradient(
    to top,
    rgba(6, 8, 18, 0.94) 0%,
    rgba(6, 8, 18, 0.72) 55%,
    transparent 100%
  );
  pointer-events: none;
}

.card-name-text {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1.35;
  color: #f5f0e8;
  text-align: center;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.65);
}

.card-status {
  margin: 3px 0 0;
  font-size: 0.62rem;
  text-align: center;
  font-weight: 600;
}

.card-status.locked {
  color: rgba(255, 255, 255, 0.45);
}

.card-status.owned-count {
  color: var(--wc-gold, #d4a574);
}
</style>
