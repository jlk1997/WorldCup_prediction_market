<template>
  <div
    class="legends-page-backdrop"
    :class="[
      { fixed, paused: paused || !visible, 'goal-active': goalFlash },
    ]"
    aria-hidden="true"
  >
    <div class="legends-row">
      <div
        v-for="(legend, idx) in legends"
        :key="legend.id"
        class="legend-figure"
        :class="[`pos-${legend.id}`, { spotlight: spotlightIdx === idx }]"
        :style="{ '--accent': legend.accent, '--delay': `${idx * 1.4}s` }"
      >
        <div class="figure-shell">
          <img
            :src="legend.imageBackdrop"
            alt=""
            :loading="idx === 1 ? 'eager' : 'lazy'"
            decoding="async"
            draggable="false"
            :fetchpriority="idx === 1 ? 'high' : 'low'"
          />
        </div>
      </div>
    </div>
    <div class="backdrop-vignette" />
    <div v-if="goalFlash" class="goal-flash" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LEGEND_CARDS } from '@/data/legends'
import { useDocumentVisible } from '@/composables/useDocumentVisible'
import { useStadiumStore } from '@/stores/stadiumStore'
import { warmLegendBackdropImages } from '@/utils/legendsImageCache'

withDefaults(
  defineProps<{
    /** fixed = App 全站底层；embedded = 首页 Dashboard 内嵌 */
    fixed?: boolean
  }>(),
  { fixed: true },
)

const legends = LEGEND_CARDS
const spotlightIdx = ref(1)
const visible = useDocumentVisible()
const { effectiveMode, goalFlash, uiOverlayOpen } = useStadiumStore()

const animateBg = computed(() => effectiveMode.value === 'high' || effectiveMode.value === 'auto')
const paused = computed(() => !animateBg.value || uiOverlayOpen.value)

let timer: ReturnType<typeof setInterval> | null = null

function startSpotlight() {
  if (timer || paused.value) return
  timer = setInterval(() => {
    spotlightIdx.value = (spotlightIdx.value + 1) % legends.length
  }, 7000)
}

function stopSpotlight() {
  if (!timer) return
  clearInterval(timer)
  timer = null
}

watch([visible, paused], ([vis, p]) => {
  if (vis && !p) startSpotlight()
  else stopSpotlight()
})

onMounted(() => {
  void warmLegendBackdropImages()
  if (visible.value && !paused.value) startSpotlight()
})

onBeforeUnmount(stopSpotlight)
</script>

<style scoped>
.legends-page-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  contain: strict;
}

.legends-page-backdrop.fixed {
  position: fixed;
  z-index: 0;
}

.legends-row {
  position: absolute;
  left: 0;
  right: 0;
  top: 4%;
  bottom: 0;
  display: flex;
  align-items: flex-end;
  gap: 0;
}

.legend-figure {
  flex: 1 1 33.333%;
  min-width: 0;
  height: 100%;
  opacity: 0.38;
  transition: opacity 1.2s ease;
  will-change: transform, opacity;
  animation: drift 8s ease-in-out infinite;
  animation-delay: var(--delay);
}

.legend-figure.spotlight {
  opacity: 0.52;
}

.pos-messi {
  animation-duration: 7s;
}

.figure-shell {
  width: 100%;
  height: 100%;
}

.figure-shell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  mask-image: linear-gradient(to top, transparent 0%, rgba(0, 0, 0, 0.25) 12%, #000 48%);
  -webkit-mask-image: linear-gradient(to top, transparent 0%, rgba(0, 0, 0, 0.25) 12%, #000 48%);
}

.backdrop-vignette {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 90% 75% at 50% 58%, transparent 30%, rgba(8, 10, 22, 0.5) 100%),
    linear-gradient(to top, rgba(8, 10, 22, 0.62) 0%, transparent 38%);
  pointer-events: none;
}

.goal-flash {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 40%, rgba(210, 167, 109, 0.35), transparent 65%);
  animation: goal-pulse 2s ease-out forwards;
  pointer-events: none;
}

.paused .legend-figure {
  animation-play-state: paused;
}

@keyframes drift {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes goal-pulse {
  0% {
    opacity: 0.9;
  }
  100% {
    opacity: 0;
  }
}

@media (max-width: 768px) {
  .legends-row {
    top: 12%;
  }

  .legend-figure {
    opacity: 0.32;
  }

  .legend-figure.spotlight {
    opacity: 0.46;
  }
}

@media (prefers-reduced-motion: reduce) {
  .legend-figure {
    animation: none !important;
  }
}
</style>
