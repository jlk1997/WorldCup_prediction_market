<template>
  <el-dialog
    v-model="visible"
    width="92%"
    class="card-reveal-dialog"
    align-center
    :show-close="true"
    :lock-scroll="false"
    :close-on-click-modal="false"
    @closed="onClosed"
  >
    <div
      class="reveal-wrap"
      :class="[
        `rarity-${primaryRarity}`,
        { 'is-duplicate': isDuplicate, 'stage-ready': stage >= 1 },
      ]"
    >
      <div v-if="stage >= 1" class="reveal-burst" aria-hidden="true">
        <span v-for="n in burstCount" :key="n" class="burst-particle" :style="{ '--i': n }" />
      </div>
      <div class="reveal-glow" aria-hidden="true" />

      <Transition name="reveal-fade">
        <p v-if="stage >= 1 && contextLine" class="reveal-context">{{ contextLine }}</p>
      </Transition>
      <Transition name="reveal-fade">
        <h2 v-if="stage >= 2" class="reveal-title">{{ title }}</h2>
      </Transition>
      <Transition name="reveal-fade">
        <p v-if="stage >= 2 && cardLine" class="reveal-sub">{{ cardLine }}</p>
      </Transition>

      <div class="cards-row">
        <CardItem
          v-for="(card, idx) in cards"
          :key="`${card.code}-${idx}`"
          :card="{ ...card, owned: true }"
          :reveal="stage >= 3"
          :reveal-delay="idx * 140"
          :reveal-duplicate="!!card.is_duplicate"
        />
      </div>

      <Transition name="reveal-fade">
        <p v-if="stage >= 4 && shardLine" class="shard-line">{{ shardLine }}</p>
      </Transition>
      <Transition name="reveal-fade">
        <p v-if="stage >= 4 && chainHint" class="chain-hint">{{ chainHint }}</p>
      </Transition>
      <Transition name="reveal-fade">
        <p v-if="stage >= 4" class="compliance">{{ complianceNotice }}</p>
      </Transition>

      <Transition name="reveal-fade">
        <div v-if="stage >= 4" class="actions">
          <el-button type="primary" @click="goCollection">查看收藏册</el-button>
          <el-button plain @click="shareCard">分享卡牌</el-button>
          <el-button plain @click="visible = false">太棒了</el-button>
        </div>
      </Transition>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import CardItem from './CardItem.vue'
import type { CollectibleDropResult } from '@/api/collectible'
import { RARITY_LABELS } from '@/api/collectible'
import { openCollectibleShare } from '@/composables/useCollectibleShareSheet'
import { cleanupElementScrollLock } from '@/utils/scrollRoot'

const props = defineProps<{
  modelValue: boolean
  drop: CollectibleDropResult | null
  complianceNotice?: string
  subtitleOverride?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean]; closed: [] }>()

const router = useRouter()
const stage = ref(0)
let stageTimers: ReturnType<typeof setTimeout>[] = []

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const cards = computed(() => props.drop?.cards ?? [])
const primaryRarity = computed(() => cards.value[0]?.rarity ?? 'common')
const isDuplicate = computed(() => !!cards.value[0]?.is_duplicate)

const burstCount = computed(() => {
  const map: Record<string, number> = { common: 8, rare: 10, epic: 12, legend: 16 }
  return map[primaryRarity.value] ?? 8
})

const title = computed(() => {
  if (!props.drop?.dropped || !cards.value.length) return '继续加油'
  const card = cards.value[0]
  if (card.is_duplicate) return '获得球星碎片'
  return `获得 ${RARITY_LABELS[card.rarity]}球星卡`
})

const contextLine = computed(() => props.subtitleOverride || '')

const cardLine = computed(() => {
  const card = cards.value[0]
  if (!card) return ''
  if (card.is_duplicate) return `${card.name} 重复，已转为碎片`
  return card.name
})

const shardLine = computed(() => {
  const card = cards.value[0]
  if (card?.shards_gained) return `+${card.shards_gained} ${RARITY_LABELS[card.rarity]}碎片`
  const shards = props.drop?.shards ?? []
  if (!shards.length) return ''
  const s = shards[0]
  return `+${s.amount} ${RARITY_LABELS[s.rarity]}碎片`
})

const chainHint = computed(() => {
  const card = cards.value[0]
  if (!card || card.is_duplicate) return ''
  if (card.chain?.status === 'minted') return '文昌链凭证已铸造'
  if (props.drop?.chain_enabled) return '文昌链数字藏品铸造中，可在收藏册查看进度'
  return ''
})

const complianceNotice =
  props.complianceNotice ||
  '数字藏品为平台内虚拟收藏，无金钱价值，不可交易、不可转赠、不可提现。'

function clearStageTimers() {
  stageTimers.forEach(clearTimeout)
  stageTimers = []
}

function resetStage() {
  clearStageTimers()
  stage.value = 0
}

function runRevealSequence() {
  resetStage()
  if (!visible.value) return
  stageTimers.push(setTimeout(() => { stage.value = 1 }, 60))
  stageTimers.push(setTimeout(() => { stage.value = 2 }, 380))
  stageTimers.push(setTimeout(() => { stage.value = 3 }, 620))
  stageTimers.push(setTimeout(() => { stage.value = 4 }, 1050))
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) void nextTick(runRevealSequence)
    else resetStage()
  },
)

function onClosed() {
  resetStage()
  cleanupElementScrollLock()
  emit('closed')
}

function goCollection() {
  visible.value = false
  router.push('/collection')
}

function shareCard() {
  const card = cards.value[0]
  if (!card) return
  openCollectibleShare({
    card: { ...card, owned: !card.is_duplicate },
    subtitleOverride: card.is_duplicate
      ? `重复卡已转碎片 +${card.shards_gained ?? 0}`
      : undefined,
  })
}
</script>

<style scoped>
.reveal-wrap {
  position: relative;
  text-align: center;
  padding: 8px 4px 4px;
  min-height: 280px;
}

.reveal-glow {
  position: absolute;
  inset: -10% 5% auto;
  height: 200px;
  border-radius: 50%;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.6s ease;
  background: radial-gradient(
    ellipse at center,
    rgba(158, 176, 200, 0.45) 0%,
    rgba(158, 176, 200, 0.12) 45%,
    transparent 72%
  );
}

.stage-ready .reveal-glow {
  opacity: 0.55;
}

.reveal-wrap.rarity-rare .reveal-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(126, 184, 255, 0.5) 0%,
    rgba(126, 184, 255, 0.14) 45%,
    transparent 72%
  );
}

.reveal-wrap.rarity-epic .reveal-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(201, 120, 138, 0.52) 0%,
    rgba(201, 120, 138, 0.16) 45%,
    transparent 72%
  );
}

.reveal-wrap.rarity-legend .reveal-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(232, 197, 71, 0.58) 0%,
    rgba(232, 197, 71, 0.18) 45%,
    transparent 72%
  );
}

.reveal-burst {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}

.burst-particle {
  position: absolute;
  left: 50%;
  top: 38%;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--wc-gold, #d4a574);
  opacity: 0;
  animation: burst-out 0.85s ease-out both;
  animation-delay: calc(var(--i) * 35ms);
  transform: rotate(calc(var(--i) * 22.5deg)) translateY(0);
}

.reveal-wrap.rarity-rare .burst-particle { background: #7eb8ff; }
.reveal-wrap.rarity-epic .burst-particle { background: #e8a0b0; }
.reveal-wrap.rarity-legend .burst-particle { background: #ffe566; }

@keyframes burst-out {
  0% { opacity: 0; transform: rotate(calc(var(--i) * 22.5deg)) translateY(0) scale(0.3); }
  25% { opacity: 1; }
  100% { opacity: 0; transform: rotate(calc(var(--i) * 22.5deg)) translateY(-72px) scale(0.6); }
}

.reveal-title {
  margin: 0 0 6px;
  font-size: 1.35rem;
  color: var(--wc-gold, #d4a574);
}

.reveal-sub {
  margin: 0 0 16px;
  color: var(--wc-text-muted);
}

.reveal-context {
  margin: 0 0 6px;
  font-size: 0.78rem;
  color: #7eb8ff;
  letter-spacing: 0.04em;
}

.cards-row {
  display: flex;
  justify-content: center;
  gap: 12px;
  max-width: min(240px, 88vw);
  margin: 0 auto 12px;
}

.is-duplicate .cards-row {
  max-width: min(200px, 80vw);
}

.shard-line {
  color: #3dd68c;
  font-size: 0.95rem;
  font-weight: 600;
  animation: shard-pulse 1.2s ease-in-out infinite;
}

@keyframes shard-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.85; transform: scale(1.03); }
}

.chain-hint {
  color: #7eb8ff;
  font-size: 0.75rem;
  margin: 0 0 8px;
}

.compliance {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
  margin: 12px 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.reveal-fade-enter-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}

.reveal-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
</style>
