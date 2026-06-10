<template>
  <div class="legends-showcase" :class="[`variant-${variant}`, { 'no-labels': !showLabels }]">
    <div v-if="title" class="showcase-head">
      <span class="showcase-kicker">传奇最后一舞</span>
      <h2 v-if="title">{{ title }}</h2>
    </div>

    <div class="legend-grid" role="list">
      <article
        v-for="(legend, idx) in legends"
        :key="legend.id"
        class="legend-card"
        :class="[`legend-${legend.id}`, { 'is-active': activeIdx === idx }]"
        :style="{ '--legend-accent': legend.accent, '--stagger': `${idx * 120}ms` }"
        role="listitem"
        @mouseenter="activeIdx = idx"
        @mouseleave="activeIdx = -1"
        @focusin="activeIdx = idx"
        @focusout="activeIdx = -1"
      >
        <div class="card-glow" aria-hidden="true" />
        <div class="card-frame">
          <div class="image-wrap">
            <img
              :src="legend.image"
              :alt="`${legend.name} 动感肖像`"
              loading="lazy"
              decoding="async"
              draggable="false"
            />
            <div class="shine" aria-hidden="true" />
            <div class="energy-lines" aria-hidden="true">
              <span /><span /><span />
            </div>
          </div>
          <div v-if="showLabels" class="card-meta">
            <strong class="legend-name">{{ legend.name }}</strong>
            <span class="legend-tag">{{ legend.tagline }}</span>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { LEGEND_CARDS, type LegendCard } from '../data/legends'

withDefaults(
  defineProps<{
    variant?: 'hero' | 'banner' | 'strip'
    title?: string
    showLabels?: boolean
    legends?: LegendCard[]
  }>(),
  {
    variant: 'banner',
    title: '',
    showLabels: true,
    legends: () => LEGEND_CARDS,
  },
)

const activeIdx = ref(-1)
</script>

<style scoped>
.legends-showcase {
  --legend-radius: 16px;
  width: 100%;
}

.showcase-head {
  margin-bottom: 12px;
}

.showcase-kicker {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wc-accent-gold);
  margin-bottom: 4px;
}

.showcase-head h2 {
  margin: 0;
  font-size: 1.05rem;
  color: #f5f0e8;
  font-weight: 800;
}

.legend-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.legend-card {
  position: relative;
  border-radius: var(--legend-radius);
  animation: legendEnter 0.7s ease backwards;
  animation-delay: var(--stagger);
}

.card-glow {
  position: absolute;
  inset: -2px;
  border-radius: calc(var(--legend-radius) + 2px);
  background: radial-gradient(circle at 50% 80%, color-mix(in srgb, var(--legend-accent) 45%, transparent), transparent 70%);
  opacity: 0.55;
  filter: blur(8px);
  animation: glowPulse 3.2s ease-in-out infinite;
  animation-delay: var(--stagger);
}

.card-frame {
  position: relative;
  border-radius: var(--legend-radius);
  overflow: hidden;
  border: 1px solid rgba(212, 165, 116, 0.22);
  background: linear-gradient(160deg, rgba(18, 22, 42, 0.95), rgba(8, 10, 22, 0.98));
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  transition: transform 0.35s ease, box-shadow 0.35s ease, border-color 0.35s ease;
}

.legend-card.is-active .card-frame,
.legend-card:focus-within .card-frame {
  transform: translateY(-4px) scale(1.02);
  border-color: color-mix(in srgb, var(--legend-accent) 55%, rgba(212, 165, 116, 0.3));
  box-shadow:
    0 12px 32px rgba(0, 0, 0, 0.45),
    0 0 24px color-mix(in srgb, var(--legend-accent) 25%, transparent);
}

.image-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  animation: legendFloat 4.5s ease-in-out infinite;
  animation-delay: var(--stagger);
}

.image-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  transform-origin: center 20%;
  animation: kenBurns 8s ease-in-out infinite alternate;
  animation-delay: var(--stagger);
  filter: contrast(1.08) saturate(1.12);
}

.image-wrap::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(8, 10, 22, 0.92) 0%,
    rgba(8, 10, 22, 0.15) 45%,
    transparent 70%
  );
  pointer-events: none;
}

.shine {
  position: absolute;
  inset: -40% -60%;
  background: linear-gradient(
    105deg,
    transparent 42%,
    rgba(255, 255, 255, 0.18) 50%,
    transparent 58%
  );
  transform: translateX(-120%);
  animation: shineSweep 4.8s ease-in-out infinite;
  animation-delay: calc(var(--stagger) + 0.6s);
  pointer-events: none;
}

.energy-lines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.energy-lines span {
  position: absolute;
  height: 2px;
  width: 40%;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--legend-accent), transparent);
  opacity: 0;
  animation: energyStreak 3.6s ease-in-out infinite;
}

.energy-lines span:nth-child(1) {
  top: 28%;
  left: -10%;
  animation-delay: calc(var(--stagger) + 0.2s);
}

.energy-lines span:nth-child(2) {
  top: 52%;
  right: -10%;
  animation-delay: calc(var(--stagger) + 1.1s);
}

.energy-lines span:nth-child(3) {
  bottom: 22%;
  left: 5%;
  animation-delay: calc(var(--stagger) + 2s);
}

.card-meta {
  padding: 8px 10px 10px;
  text-align: center;
}

.legend-name {
  display: block;
  font-size: 0.88rem;
  color: #f5f0e8;
  letter-spacing: 0.04em;
}

.legend-tag {
  display: block;
  margin-top: 2px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}

/* Variants */
.variant-hero .legend-grid {
  gap: 14px;
}

.variant-hero .image-wrap {
  aspect-ratio: 2 / 3;
}

.variant-banner {
  margin-bottom: 4px;
}

.variant-banner .legend-grid {
  gap: 8px;
}

.variant-banner .card-meta {
  padding: 6px 8px 8px;
}

.variant-banner .legend-name {
  font-size: 0.78rem;
}

.variant-banner .legend-tag {
  font-size: 0.62rem;
}

.variant-strip .showcase-head {
  display: none;
}

.variant-strip .legend-grid {
  gap: 8px;
}

.variant-strip .image-wrap {
  aspect-ratio: 4 / 5;
}

.no-labels .card-meta {
  display: none;
}

.no-labels .image-wrap::after {
  background: linear-gradient(to top, rgba(8, 10, 22, 0.5) 0%, transparent 55%);
}

@keyframes legendEnter {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes legendFloat {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

@keyframes kenBurns {
  from {
    transform: scale(1.02);
  }
  to {
    transform: scale(1.1);
  }
}

@keyframes shineSweep {
  0%,
  72% {
    transform: translateX(-120%);
  }
  100% {
    transform: translateX(120%);
  }
}

@keyframes glowPulse {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 0.85;
  }
}

@keyframes energyStreak {
  0%,
  100% {
    opacity: 0;
    transform: translateX(0) scaleX(0.6);
  }
  15% {
    opacity: 0.75;
  }
  45% {
    opacity: 0;
    transform: translateX(120%) scaleX(1);
  }
}

@media (max-width: 768px) {
  .variant-hero .legend-grid {
    gap: 8px;
  }

  .variant-banner .legend-tag {
    display: none;
  }

  .variant-strip .image-wrap {
    aspect-ratio: 3 / 4;
  }
}

@media (prefers-reduced-motion: reduce) {
  .legend-card,
  .image-wrap,
  .image-wrap img,
  .shine,
  .card-glow,
  .energy-lines span {
    animation: none !important;
  }

  .legend-card.is-active .card-frame {
    transform: none;
  }
}
</style>
