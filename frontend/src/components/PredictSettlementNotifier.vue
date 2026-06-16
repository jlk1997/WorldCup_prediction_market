<template>
  <el-popover v-if="isLoggedIn && (latest || unread || streakRisk)" placement="bottom" :width="340" trigger="click">
    <template #reference>
      <el-badge :value="badgeCount" :hidden="!badgeCount" class="settle-badge">
        <el-button circle size="small" aria-label="竞猜结算通知">
          <span>🎯</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="streakRisk" class="settle-pop streak-pop">
      <strong>连胜守护</strong>
      <p>{{ streakRisk.message }}</p>
      <el-button type="warning" size="small" @click="goStreakProtect">
        再猜一场保连胜
      </el-button>
    </div>
    <div v-if="latest" class="settle-pop" :class="{ 'with-border': streakRisk }">
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
      <div class="pop-actions">
        <el-button
          v-if="latest.payload?.next_match_id"
          type="primary"
          size="small"
          @click="goNext(latest.payload.next_match_id as number)"
        >
          去猜下一场
        </el-button>
        <el-button link size="small" @click="markRead">知道了</el-button>
      </div>
    </div>
    <div v-else-if="unread && !latest" class="settle-pop">
      <p>你有 {{ unread }} 条未读结算通知</p>
      <el-button link size="small" @click="$router.push('/me?focus=predictions')">去查看</el-button>
    </div>
    <div v-else-if="pendingCount > 0 && !latest" class="settle-pop">
      <p>⏳ {{ pendingCount }} 场待开奖</p>
      <el-button link size="small" @click="$router.push('/me?focus=predictions')">查看进度</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { markPredictRead, predictNotify } from '../stores/headerNotificationsStore'
import { isLoggedIn, fetchMe } from '../stores/authStore'
import { getDailyStatus, type DailyStatus } from '../api/commerce'

const router = useRouter()
const unread = computed(() => predictNotify.unread)
const latest = computed(() => predictNotify.latest)
const dailyStatus = ref<DailyStatus | null>(null)

const streakRisk = computed(() => dailyStatus.value?.streak_risk ?? null)
const pendingCount = computed(() => dailyStatus.value?.pending_predictions ?? 0)

const badgeCount = computed(() => {
  let n = unread.value
  if (streakRisk.value && (streakRisk.value.win_streak ?? 0) >= 2) n += 1
  return n
})

async function refreshDaily() {
  if (!isLoggedIn.value) {
    dailyStatus.value = null
    return
  }
  dailyStatus.value = await getDailyStatus().catch(() => null)
}

async function markRead() {
  await markPredictRead(async () => {
    await fetchMe()
    window.dispatchEvent(new CustomEvent('predict-records-refresh'))
  })
}

function goNext(matchId: number) {
  markRead()
  router.push({ path: '/predict', query: { highlight: String(matchId) } })
}

function goStreakProtect() {
  const mid = streakRisk.value?.match_id
  router.push(mid ? { path: '/predict', query: { highlight: String(mid) } } : '/predict')
}

onMounted(() => void refreshDaily())
watch(isLoggedIn, () => void refreshDaily())
watch(
  () => predictNotify.unread,
  () => void refreshDaily(),
)
</script>

<style scoped>
.settle-badge {
  margin-right: 4px;
}
.settle-pop p {
  margin: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wc-text-muted, #9a94a8);
}
.settle-pop.with-border {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.streak-pop strong {
  color: #e6a23c;
}
.pop-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
