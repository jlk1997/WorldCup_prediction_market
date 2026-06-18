<template>

  <div class="set-card glass-panel">

    <div class="set-head">

      <h3>{{ set.name }}</h3>

      <span class="progress">{{ set.owned_count }}/{{ set.total_count }}</span>

    </div>

    <p v-if="set.description" class="set-desc">{{ set.description }}</p>

    <el-progress

      :percentage="progressPct"

      :stroke-width="8"

      :color="set.complete ? '#3dd68c' : '#d4a574'"

    />

    <p v-if="missingPreview" class="missing-hint">还差：{{ missingPreview }}</p>

    <div v-if="set.reward?.badge_title" class="reward-preview">

      奖励：{{ set.reward.badge_title }}

      <span v-if="set.reward.fan_coins"> · +{{ set.reward.fan_coins }} 币</span>

      <span v-if="set.reward.redeem_points"> · +{{ set.reward.redeem_points }} 可用分</span>

    </div>

    <el-button

      v-if="set.complete && !set.claimed"

      type="primary"

      size="small"

      :loading="claiming"

      @click="$emit('claim', set.code)"

    >

      领取套组奖励

    </el-button>

    <el-tag v-else-if="set.claimed" type="success" size="small">已领取</el-tag>

  </div>

</template>



<script setup lang="ts">

import { computed } from 'vue'

import type { CardSetProgress } from '@/api/collectible'



const props = defineProps<{ set: CardSetProgress; claiming?: boolean }>()

defineEmits<{ claim: [string] }>()



const progressPct = computed(() => {

  if (!props.set.total_count) return 0

  return Math.min(100, Math.round((props.set.owned_count / props.set.total_count) * 100))

})



const missingPreview = computed(() => {

  const names = props.set.missing_names || props.set.missing_codes || []

  if (!names.length || props.set.complete) return ''

  const show = names.slice(0, 3)

  const extra = names.length > 3 ? ` 等${names.length}张` : ''

  return `${show.join('、')}${extra}`

})

</script>



<style scoped>

.set-card {

  padding: 14px 16px;

  border-radius: 12px;

}

.set-head {

  display: flex;

  justify-content: space-between;

  align-items: center;

  gap: 8px;

}

.set-head h3 {

  margin: 0;

  font-size: 0.95rem;

}

.progress {

  font-size: 0.8rem;

  color: var(--wc-gold);

}

.set-desc {

  margin: 6px 0 10px;

  font-size: 0.78rem;

  color: var(--wc-text-muted);

}

.missing-hint {

  margin: 8px 0 0;

  font-size: 0.72rem;

  color: rgba(126, 184, 255, 0.95);

  line-height: 1.4;

}

.reward-preview {

  margin: 10px 0;

  font-size: 0.75rem;

  color: var(--wc-text-muted);

}

</style>


