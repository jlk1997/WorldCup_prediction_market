<template>

  <div v-if="visible" class="pass-nudge glass-panel">

    <div class="pass-nudge-main">

      <div class="pass-head-row">

        <span class="pass-tag">藏品手册</span>

        <span v-if="claimableCount" class="claim-badge">{{ claimableCount }} 可领</span>

      </div>

      <strong class="pass-title">{{ nudge!.title }}</strong>

      <p class="pass-body">{{ nudge!.body }}</p>

      <p v-if="premiumHint" class="pass-premium">{{ premiumHint }}</p>

    </div>

    <div class="pass-actions">

      <el-button type="primary" size="small" @click="goPass">

        {{ claimableCount ? '一键领取' : '查看手册' }}

      </el-button>

      <el-button

        v-if="!nudge!.premium_unlocked"

        size="small"

        plain

        @click="goShop"

      >

        解锁尊享

      </el-button>

      <button type="button" class="dismiss-btn" @click="dismiss">稍后</button>

    </div>

  </div>

</template>



<script setup lang="ts">

import { computed, onMounted, ref } from 'vue'

import { useRouter } from 'vue-router'

import type { DailyStatus } from '@/api/commerce'

import { authState } from '@/stores/authStore'

import { collectionPassNudge } from '@/stores/dailyStatusStore'

import { trackEvent } from '@/utils/analytics'



const props = defineProps<{

  status?: DailyStatus | null

  requireActive?: boolean

}>()



const router = useRouter()

const dismissed = ref(false)

const DISMISS_KEY = 'wc_collection_pass_nudge_dismissed_at'

const DISMISS_MS = 12 * 60 * 60 * 1000



const nudge = computed(() => props.status?.collection_pass_nudge ?? collectionPassNudge.value)

const claimableCount = computed(() => nudge.value?.claimable_count ?? 0)



const premiumHint = computed(() => {

  if (claimableCount.value) return null

  if (!nudge.value?.next_premium_card) return null

  if (nudge.value.premium_unlocked) return '尊享已解锁 · 升级后可领限定卡'

  return '解锁尊享可领手册限定卡'

})



const visible = computed(() => {

  if (!authState.accessToken || dismissed.value || !nudge.value) return false

  if (props.requireActive !== false) {
    const seg = props.status?.activation_segment
    const hasCardsNoDuel =
      (props.status?.card_owned_count ?? 0) > 0 &&
      (props.status?.duel_segment === 'never_dueled' || props.status?.duel_segment === 'one_duel')
    if (seg && seg !== 'active' && !hasCardsNoDuel) return false
  }

  return true

})



function isDismissedRecently() {

  try {

    const raw = localStorage.getItem(DISMISS_KEY)

    if (!raw) return false

    return Date.now() - Number(raw) < DISMISS_MS

  } catch {

    return false

  }

}



function dismiss() {

  try {

    localStorage.setItem(DISMISS_KEY, String(Date.now()))

  } catch {

    /* ignore */

  }

  dismissed.value = true

}



function goPass() {
  trackEvent('collection_pass_nudge_click', { target: 'pass', claimable: claimableCount.value })
  if (claimableCount.value) {
    router.push('/collection?tab=pass&claim=all')
    return
  }
  router.push(nudge.value?.path || '/collection?tab=pass')
}



function goShop() {

  trackEvent('collection_pass_nudge_click', { target: 'shop' })

  router.push('/shop?highlight=collection_pass')

}



onMounted(() => {

  dismissed.value = isDismissedRecently()

})

</script>



<style scoped>

.pass-nudge {

  display: flex;

  flex-direction: column;

  gap: 12px;

  padding: 14px 16px;

  margin-top: 10px;

  border: 1px solid rgba(212, 165, 116, 0.35);

  background: linear-gradient(135deg, rgba(212, 165, 116, 0.1), rgba(126, 184, 255, 0.06));

  border-radius: 14px;

}



.pass-head-row {

  display: flex;

  align-items: center;

  gap: 8px;

  margin-bottom: 4px;

}



.pass-tag {

  font-size: 0.68rem;

  font-weight: 600;

  color: var(--wc-accent-gold, #d4a574);

}



.claim-badge {

  font-size: 0.65rem;

  padding: 2px 8px;

  border-radius: 999px;

  background: rgba(61, 214, 140, 0.15);

  color: #3dd68c;

  font-weight: 600;

}



.pass-title {

  display: block;

  font-size: 0.98rem;

  color: #f5f0e8;

  margin: 0 0 4px;

}



.pass-body,

.pass-premium {

  margin: 0;

  font-size: 0.78rem;

  color: var(--wc-text-muted);

  line-height: 1.45;

}



.pass-premium {

  color: #7eb8ff;

  margin-top: 4px;

}



.pass-actions {

  display: flex;

  gap: 8px;

  flex-wrap: wrap;

  align-items: center;

}



.dismiss-btn {

  border: none;

  background: transparent;

  color: var(--wc-text-muted);

  font-size: 0.75rem;

  cursor: pointer;

  padding: 6px 8px;

  margin-left: auto;

}



.dismiss-btn:hover {

  color: #f5f0e8;

}



@media (min-width: 520px) {

  .pass-nudge {

    flex-direction: row;

    align-items: center;

    justify-content: space-between;

  }



  .dismiss-btn {

    margin-left: 0;

  }

}

</style>

