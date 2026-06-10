<template>
  <div class="stadium-wrapper" :class="{ 'passive-touch': passiveTouch }">
    <div v-if="showLiteBg" class="lite-background"></div>
    <div v-else ref="threeContainer" class="three-background"></div>

    <div v-if="matchContext" class="scoreboard glass-panel">
      <div class="sb-teams">{{ matchContext.team1 }} vs {{ matchContext.team2 }}</div>
      <div class="sb-score">
        {{ matchContext.homeScore ?? 0 }} : {{ matchContext.awayScore ?? 0 }}
      </div>
      <div v-if="matchContext.status === 'live'" class="sb-live">
        LIVE {{ matchContext.minute }}'
      </div>
    </div>

    <div v-if="goalFlash" class="goal-flash"></div>
    <div
      v-if="analyzing"
      class="analyze-pulse"
      :class="{ 'analyze-pulse-lite': !useFullAnalyzePulse }"
    ></div>

    <div v-if="matchContext?.formationDots?.length && useHighQuality3D" class="formation-overlay">
      <div
        v-for="(dot, i) in matchContext.formationDots"
        :key="i"
        class="formation-dot"
        :class="dot.side"
        :style="{ left: dot.x + '%', top: dot.y + '%' }"
        :title="dot.name"
      />
    </div>

    <canvas
      v-if="heatmapData && useHighQuality3D"
      ref="heatmapCanvas"
      class="heatmap-canvas"
      width="176"
      height="80"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, watch, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useStadiumStore } from '@/stores/stadiumStore'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { resolveStadiumPreset, DEFAULT_PRESET } from '@/config/stadiumPresets'

type Vec3 = { x: number; y: number; z: number }
type ThreeModule = typeof import('three')
type QualityTier = 'high' | 'low'

const route = useRoute()
const { isMobile } = useBreakpoint()
const {
  useThreeJs,
  useHighQuality3D,
  useFullAnalyzePulse,
  matchContext,
  goalFlash,
  analyzing,
  heatmapData,
  uiOverlayOpen,
} = useStadiumStore()

const threeContainer = ref<HTMLElement | null>(null)
const heatmapCanvas = ref<HTMLCanvasElement | null>(null)
const glbLoadFailed = ref(false)

/** 赛事大屏（/）不挂载本组件；其余非轻量页面启用 3D 球场 */
const showLiteBg = computed(() => !useThreeJs.value || glbLoadFailed.value)

const qualityTier = computed<QualityTier>(() => (useHighQuality3D.value ? 'high' : 'low'))

const passiveTouch = computed(
  () => isMobile.value && !route.path.startsWith('/agent'),
)

let THREE: ThreeModule | null = null
let scene: import('three').Scene | null = null
let camera: import('three').PerspectiveCamera | null = null
let renderer: import('three').WebGLRenderer | null = null
let controls: import('three/examples/jsm/controls/OrbitControls.js').OrbitControls | null = null
let animationId = 0
let lastFrame = 0
let isPaused = false
let initToken = 0
let fpsCap = 20
const targetCameraPos: Vec3 = { x: 0, y: 110, z: 150 }
const targetControlsTarget: Vec3 = { x: 0, y: -10, z: 0 }
let isUserInteracting = false

function applyQualitySettings(tier: QualityTier) {
  fpsCap = tier === 'high' ? 30 : 20
  if (!renderer) return
  renderer.setPixelRatio(
    tier === 'high' ? Math.min(window.devicePixelRatio, 1.5) : 1,
  )
  if (controls) {
    controls.autoRotateSpeed = tier === 'high' ? 0.45 : 0.32
  }
}

function applyStadiumPreset() {
  const preset = matchContext.value?.stadium
    ? resolveStadiumPreset(matchContext.value.stadium)
    : DEFAULT_PRESET
  targetCameraPos.x = preset.camera.x
  targetCameraPos.y = preset.camera.y
  targetCameraPos.z = preset.camera.z
  targetControlsTarget.x = preset.lookAt.x
  targetControlsTarget.y = preset.lookAt.y
  targetControlsTarget.z = preset.lookAt.z
}

function disposeThreeJS() {
  initToken += 1
  window.removeEventListener('resize', onWindowResize)
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = 0
  }
  controls?.dispose?.()
  controls = null
  if (renderer) {
    renderer.dispose()
    if (threeContainer.value?.contains(renderer.domElement)) {
      threeContainer.value.removeChild(renderer.domElement)
    }
  }
  renderer = null
  scene = null
  camera = null
}

function onWindowResize() {
  if (!threeContainer.value || !camera || !renderer) return
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
}

function animate(now: number) {
  if (isPaused || !renderer || !scene || !camera || !controls || !THREE) return
  animationId = requestAnimationFrame(animate)
  const minInterval = 1000 / fpsCap
  if (now - lastFrame < minInterval) return
  lastFrame = now

  if (!isUserInteracting) {
    camera.position.x += (targetCameraPos.x - camera.position.x) * 0.02
    camera.position.y += (targetCameraPos.y - camera.position.y) * 0.02
    camera.position.z += (targetCameraPos.z - camera.position.z) * 0.02
    controls.target.x += (targetControlsTarget.x - controls.target.x) * 0.02
    controls.target.y += (targetControlsTarget.y - controls.target.y) * 0.02
    controls.target.z += (targetControlsTarget.z - controls.target.z) * 0.02
  }
  controls.update()
  renderer.render(scene, camera)
}

function startAnimation() {
  if (animationId || !renderer || !useThreeJs.value) return
  isPaused = false
  animate(performance.now())
}

function pauseAnimation() {
  isPaused = true
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = 0
  }
}

async function initThreeJS() {
  disposeThreeJS()
  const token = initToken
  const container = threeContainer.value
  if (!container || !useThreeJs.value) return

  if (!THREE) {
    THREE = await import('three')
  }
  if (token !== initToken) return

  const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js')
  const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
  if (token !== initToken) return

  const tier = qualityTier.value

  scene = new THREE.Scene()
  scene.background = null

  const width = window.innerWidth
  const height = window.innerHeight

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 10000)
  camera.position.set(targetCameraPos.x, targetCameraPos.y, targetCameraPos.z)

  renderer = new THREE.WebGLRenderer({
    antialias: tier === 'high',
    alpha: true,
    powerPreference: tier === 'high' ? 'high-performance' : 'default',
  })
  renderer.setSize(width, height)
  applyQualitySettings(tier)
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = tier === 'high' ? 1.2 : 1.05
  container.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0xffeedd, tier === 'high' ? 0.6 : 0.5))
  const dirLight = new THREE.DirectionalLight(0xffffff, tier === 'high' ? 1.5 : 1.1)
  dirLight.position.set(100, 200, 50)
  scene.add(dirLight)

  if (tier === 'high') {
    const goldLightLeft = new THREE.PointLight(0xd2a76d, 2000, 500)
    goldLightLeft.position.set(-50, 50, 0)
    scene.add(goldLightLeft)
  }

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.enableZoom = tier === 'high'
  controls.autoRotate = true
  controls.target.set(targetControlsTarget.x, targetControlsTarget.y, targetControlsTarget.z)
  controls.addEventListener('start', () => {
    isUserInteracting = true
  })

  const loader = new GLTFLoader()
  loader.load(
    '/stadium.glb',
    (gltf) => {
      if (token !== initToken || !scene || !THREE) return
      const stadiumModel = gltf.scene
      stadiumModel.scale.set(5, 5, 5)
      const box = new THREE!.Box3().setFromObject(stadiumModel)
      const center = box.getCenter(new THREE!.Vector3())
      stadiumModel.position.sub(center)
      stadiumModel.position.y += 5
      scene.add(stadiumModel)
    },
    undefined,
    () => {
      glbLoadFailed.value = true
      disposeThreeJS()
    },
  )

  window.addEventListener('resize', onWindowResize)
  if (!document.hidden && !uiOverlayOpen.value) startAnimation()
}

function scheduleInitThreeJS() {
  const run = () => {
    void initThreeJS()
  }
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(run, { timeout: 2000 })
  } else {
    setTimeout(run, 80)
  }
}

function drawHeatmap() {
  const canvas = heatmapCanvas.value
  const data = heatmapData.value
  if (!canvas || !data?.length) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const cellW = canvas.width / (data[0]?.length || 1)
  const cellH = canvas.height / data.length
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  data.forEach((row, ri) => {
    row.forEach((val, ci) => {
      ctx.fillStyle = `rgba(210, 167, 109, ${0.2 + val * 0.6})`
      ctx.fillRect(ci * cellW, ri * cellH, cellW - 1, cellH - 1)
    })
  })
}

function onVisibilityChange() {
  if (document.hidden) {
    pauseAnimation()
  } else if (useThreeJs.value && renderer) {
    startAnimation()
  }
}

watch(() => route.path, (newPath) => {
  isUserInteracting = false
  if (newPath.startsWith('/agent')) {
    targetCameraPos.x = 0
    targetCameraPos.y = 10
    targetCameraPos.z = 50
    targetControlsTarget.x = 0
    targetControlsTarget.y = 10
    targetControlsTarget.z = 0
  } else {
    applyStadiumPreset()
  }
  applyQualitySettings(qualityTier.value)
  if (useThreeJs.value && renderer && !document.hidden && !uiOverlayOpen.value) {
    startAnimation()
  } else {
    pauseAnimation()
  }
}, { immediate: true })

watch(qualityTier, (tier, prev) => {
  applyQualitySettings(tier)
  // 高/低画质切换需重建 renderer（抗锯齿开关）
  if (prev && tier !== prev && useThreeJs.value && !glbLoadFailed.value) {
    void nextTick().then(() => scheduleInitThreeJS())
  }
})

watch(matchContext, () => applyStadiumPreset(), { deep: true })

watch(useThreeJs, async (enabled) => {
  if (enabled && !glbLoadFailed.value) {
    await nextTick()
    scheduleInitThreeJS()
  } else {
    disposeThreeJS()
  }
}, { immediate: true })

watch(heatmapData, async () => {
  await nextTick()
  drawHeatmap()
}, { deep: true })

watch(uiOverlayOpen, (open) => {
  if (open) pauseAnimation()
  else if (useThreeJs.value && renderer && !document.hidden) startAnimation()
})

document.addEventListener('visibilitychange', onVisibilityChange)

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
  disposeThreeJS()
})
</script>

<style scoped>
.stadium-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  pointer-events: auto;
}

.stadium-wrapper.passive-touch,
.stadium-wrapper.passive-touch .three-background,
.stadium-wrapper.passive-touch .lite-background {
  pointer-events: none !important;
}

.three-background {
  width: 100%;
  height: 100%;
  pointer-events: auto;
}

.lite-background {
  position: relative;
  width: 100%;
  height: 100%;
  pointer-events: auto;
  background:
    radial-gradient(ellipse at 50% 88%, rgba(42, 110, 58, 0.42) 0%, transparent 48%),
    radial-gradient(ellipse at 50% 22%, rgba(210, 167, 109, 0.18) 0%, transparent 58%),
    linear-gradient(180deg, #0a0e14 0%, #121820 45%, #1a2e1f 100%);
  background-size: 100% 100%;
}

.lite-background::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(210, 167, 109, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(210, 167, 109, 0.04) 1px, transparent 1px);
  background-size: 36px 36px;
  pointer-events: none;
}

.scoreboard {
  position: absolute;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  text-align: center;
  pointer-events: none;
  z-index: 5;
  background: rgba(18, 18, 18, 0.75);
}

.sb-teams { font-size: 0.85rem; color: #A0A0A0; }
.sb-score { font-size: 1.8rem; font-weight: 900; color: #D2A76D; }
.sb-live { color: #f56c6c; font-size: 0.8rem; font-weight: bold; }

.goal-flash {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, rgba(255, 215, 0, 0.4) 0%, transparent 70%);
  animation: flash 2s ease-out;
  pointer-events: none;
  z-index: 4;
}

.analyze-pulse {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(210, 167, 109, 0.5);
  animation: borderPulse 1.5s infinite;
  pointer-events: none;
  z-index: 3;
}

.analyze-pulse-lite {
  inset: auto;
  top: calc(var(--wc-mobile-header-height, 52px) + 12px);
  left: 50%;
  transform: translateX(-50%);
  width: min(420px, 90vw);
  height: 48px;
  border-radius: 8px;
  animation: borderPulseLite 1.5s infinite;
}

@media (max-width: 768px) {
  .scoreboard {
    top: calc(var(--wc-mobile-header-height) + 8px);
    width: min(360px, 92vw);
    padding: 8px 16px;
  }
  .sb-score {
    font-size: 1.4rem;
  }
}

@keyframes flash {
  0% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes borderPulse {
  50% { border-color: rgba(210, 167, 109, 0.9); box-shadow: inset 0 0 40px rgba(210, 167, 109, 0.2); }
}

@keyframes borderPulseLite {
  50% { border-color: rgba(210, 167, 109, 0.85); box-shadow: 0 0 16px rgba(210, 167, 109, 0.25); }
}

@media (prefers-reduced-motion: reduce) {
  .analyze-pulse,
  .goal-flash {
    animation: none;
  }
  .analyze-pulse-lite {
    animation: none;
    border-color: rgba(210, 167, 109, 0.7);
  }
}

.heatmap-canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -40%) perspective(400px) rotateX(55deg);
  pointer-events: none;
  z-index: 2;
}

.formation-overlay {
  position: absolute;
  top: 45%;
  left: 50%;
  width: 42%;
  height: 28%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 3;
}

.formation-dot {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 8px currentColor;
}
.formation-dot.home { background: #D2A76D; color: #D2A76D; }
.formation-dot.away { background: #6eb5ff; color: #6eb5ff; }
</style>
