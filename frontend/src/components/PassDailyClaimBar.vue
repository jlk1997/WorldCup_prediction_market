<template>
  <div v-if="show" class="pass-claim-bar glass-inner">
    <span>🎫 通行证今日 {{ grant }} 球迷币未领取</span>
    <el-button type="warning" size="small" :loading="claiming" @click="claim">
      一键领取
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { DailyStatus } from '@/api/commerce'
import { claimSeasonPassDaily } from '@/api/commerce'
import { fetchMe } from '@/stores/authStore'

const props = defineProps<{ status: DailyStatus | null }>()
const emit = defineEmits<{ refresh: [] }>()

const claiming = ref(false)

const show = computed(
  () =>
    !!props.status?.pass_benefits?.active &&
    !props.status.pass_benefits.coins_claimed_today,
)

const grant = computed(() => props.status?.pass_benefits?.daily_coins_grant ?? 50)

async function claim() {
  if (claiming.value) return
  claiming.value = true
  try {
    const res = await claimSeasonPassDaily()
    if (res.granted > 0) {
      ElMessage.success(`已领取 ${res.granted} 球迷币`)
      await fetchMe()
      emit('refresh')
    } else if (res.reason === 'already_claimed') {
      ElMessage.info('今日已领取')
      emit('refresh')
    } else {
      ElMessage.warning('暂无法领取，请确认通行证是否生效')
    }
  } catch {
    ElMessage.error('领取失败，请稍后再试')
  } finally {
    claiming.value = false
  }
}
</script>

<style scoped>
.pass-claim-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.4);
  background: rgba(212, 165, 116, 0.1);
  font-size: 0.86rem;
  color: var(--wc-accent-gold, #d4a574);
}
</style>
