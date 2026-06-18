<template>
  <el-dialog
    v-model="visible"
    width="92%"
    class="card-reveal-dialog"
    align-center
    :show-close="true"
    @closed="$emit('closed')"
  >
    <div class="reveal-wrap">
      <div class="reveal-glow" :class="`rarity-${primaryRarity}`" />
      <h2 class="reveal-title">{{ title }}</h2>
      <p v-if="contextLine" class="reveal-context">{{ contextLine }}</p>
      <p v-if="cardLine" class="reveal-sub">{{ cardLine }}</p>
      <div class="cards-row">
        <CardItem
          v-for="(card, idx) in cards"
          :key="`${card.code}-${idx}`"
          :card="{ ...card, owned: true }"
        />
      </div>
      <p v-if="shardLine" class="shard-line">{{ shardLine }}</p>
      <p v-if="chainHint" class="chain-hint">{{ chainHint }}</p>
      <p class="compliance">{{ complianceNotice }}</p>
      <div class="actions">
        <el-button type="primary" @click="goCollection">查看收藏册</el-button>
        <el-button plain @click="shareCard">分享卡牌</el-button>
        <el-button plain @click="visible = false">太棒了</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import CardItem from './CardItem.vue'
import type { CollectibleDropResult } from '@/api/collectible'
import { RARITY_LABELS } from '@/api/collectible'
import { downloadSharePoster } from '@/utils/sharePoster'
import { authState } from '@/stores/authStore'

const props = defineProps<{
  modelValue: boolean
  drop: CollectibleDropResult | null
  complianceNotice?: string
  subtitleOverride?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean]; closed: [] }>()

const router = useRouter()

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const cards = computed(() => props.drop?.cards ?? [])
const primaryRarity = computed(() => cards.value[0]?.rarity ?? 'common')

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

function goCollection() {
  visible.value = false
  router.push('/collection')
}

async function shareCard() {
  const card = cards.value[0]
  if (!card) return
  await downloadSharePoster({
    variant: 'card',
    displayName: authState.user?.nickname,
    title: `我获得了 ${card.name}`,
    subtitle: `${RARITY_LABELS[card.rarity]} · 最后一舞收藏册`,
    statsLine: card.is_duplicate ? `重复卡已转碎片 +${card.shards_gained ?? 0}` : '猜中掉落 · 虚拟收藏',
    badge: '数字藏品',
  })
}
</script>

<style scoped>
.reveal-wrap {
  position: relative;
  text-align: center;
  padding: 8px 4px 4px;
}
.reveal-glow {
  position: absolute;
  inset: -20% 10% auto;
  height: 180px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.35;
  pointer-events: none;
}
.reveal-glow.rarity-legend { background: #e8c547; }
.reveal-glow.rarity-epic { background: #c9788a; }
.reveal-glow.rarity-rare { background: #7eb8ff; }
.reveal-glow.rarity-common { background: #9eb0c8; }
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
}
.cards-row {
  display: flex;
  justify-content: center;
  gap: 12px;
  max-width: 220px;
  margin: 0 auto 12px;
}
.shard-line {
  color: #3dd68c;
  font-size: 0.9rem;
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
</style>
