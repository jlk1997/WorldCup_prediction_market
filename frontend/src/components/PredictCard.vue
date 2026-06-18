<template>
  <div v-if="resolvedPredicted" class="predict-card glass-panel predicted">
    <h3>娱乐竞猜</h3>
    <p class="hint done-hint">你已参与本场竞猜</p>
    <p v-if="predictedPick" class="pick-info">你的选择：<strong>{{ predictedPick }}</strong></p>
    <p v-if="predictedStake != null" class="stake-info">
      {{ predictedFree ? '免费竞猜' : `已质押 ${predictedStake} 球迷币` }}
      <span v-if="predictedStatus === 'pending'"> · 待开奖</span>
      <span v-else-if="predictedStatus === 'won'" class="won-tag"> · 已猜中</span>
      <span v-else-if="predictedStatus === 'lost'" class="lost-tag"> · 未猜中</span>
      <span v-else-if="predictedStatus === 'void'" class="void-tag"> · 流局退款</span>
    </p>
    <el-button type="primary" plain size="small" @click="$router.push('/predict')">去竞猜大厅</el-button>
  </div>
  <div v-else class="predict-card glass-panel">
    <h3>娱乐竞猜</h3>
    <p class="hint">AI 仅供参考 · 虚拟球迷币不可提现</p>
    <el-radio-group v-model="pick" size="small">
      <el-radio-button value="home">主胜</el-radio-button>
      <el-radio-button value="draw">平局</el-radio-button>
      <el-radio-button value="away">客胜</el-radio-button>
    </el-radio-group>
    <div class="row">
      <el-checkbox v-model="useFree">今日免费竞猜</el-checkbox>
      <el-input-number v-if="!useFree" v-model="stake" :min="10" :max="500" size="small" />
      <el-button type="primary" size="small" :loading="loading" @click="submit">提交</el-button>
    </div>
    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { submitPrediction, getPredictableMatches, getMyPredictions } from '../api/commerce'
import { authState, fetchMe } from '../stores/authStore'
import { getErrorMessage, isRateLimitError } from '../api/client'
import { showApiError } from '../utils/errorHandler'

const props = defineProps<{ matchId: number; aiPick?: string }>()

const router = useRouter()
const pick = ref(props.aiPick || 'home')
const stake = ref(10)
const useFree = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const userPredicted = ref(false)
const userPick = ref<string | null>(null)
const userStake = ref<number | null>(null)
const userFree = ref(false)
const userStatus = ref<string | null>(null)

const resolvedPredicted = computed(() => userPredicted.value)

const predictedPick = computed(() => {
  if (userPick.value === 'home') return '主胜'
  if (userPick.value === 'away') return '客胜'
  if (userPick.value === 'draw') return '平局'
  return userPick.value
})

const predictedStake = computed(() => userStake.value)
const predictedFree = computed(() => userFree.value)
const predictedStatus = computed(() => userStatus.value)

onMounted(async () => {
  if (!authState.user) return
  try {
    const matches = await getPredictableMatches()
    let m = matches.find((x) => x.id === props.matchId)
    if (!m?.user_predicted) {
      const history = await getMyPredictions()
      const hist = history.find((x) => x.match_id === props.matchId)
      if (hist) {
        userPredicted.value = true
        userPick.value = hist.pick ?? null
        userStake.value = hist.stake_coins ?? null
        userFree.value = !!hist.is_free
        userStatus.value = hist.status ?? null
        return
      }
    }
    if (m?.user_predicted) {
      userPredicted.value = true
      userPick.value = m.user_pick ?? null
      userStake.value = m.user_stake_coins ?? null
      userFree.value = !!m.user_is_free
      userStatus.value = m.user_prediction_status ?? null
    }
  } catch {
    /* ignore */
  }
})

async function submit() {
  if (!authState.user) {
    router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`)
    return
  }
  errorMsg.value = ''
  loading.value = true
  try {
    const res = await submitPrediction({
      match_id: props.matchId,
      pick: pick.value,
      stake_coins: useFree.value ? 0 : stake.value,
      use_free: useFree.value,
    })
    await fetchMe()
    let msg = '竞猜已提交'
    if (res.arena_battalion_bonus && res.arena_battalion_bonus > 0) {
      msg += ` · 连击 +${res.arena_battalion_bonus} 军团贡献`
    }
    ElMessage.success(msg)
    userPredicted.value = true
    userPick.value = pick.value
    userStake.value = useFree.value ? 0 : stake.value
    userFree.value = useFree.value
    userStatus.value = 'pending'
  } catch (e) {
    showApiError(e)
    if (isRateLimitError(e) && e.notified) return
    const msg = getErrorMessage(e)
    errorMsg.value = msg
    if (msg.includes('已竞猜过')) {
      ElMessage.warning('您已参与本场竞猜')
      userPredicted.value = true
      const matches = await getPredictableMatches().catch(() => [])
      const m = matches.find((x) => x.id === props.matchId)
      if (m) {
        userPick.value = m.user_pick ?? null
        userStake.value = m.user_stake_coins ?? null
        userFree.value = !!m.user_is_free
        userStatus.value = m.user_prediction_status ?? null
      }
    } else {
      ElMessage.error(msg)
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.predict-card {
  padding: 16px 20px;
  margin-top: 16px;
}
.predict-card h3 {
  margin: 0 0 4px;
}
.hint {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  margin-bottom: 12px;
}
.done-hint {
  color: #8fd48a;
}
.pick-info,
.stake-info {
  font-size: 0.9rem;
  color: var(--wc-text-secondary);
  margin: 0 0 10px;
}
.won-tag { color: #8fd48a; }
.lost-tag { color: #f89898; }
.void-tag { color: #79bbff; }
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.error-msg {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: #f89898;
}
</style>
