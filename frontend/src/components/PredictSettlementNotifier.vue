<template>
  <el-popover v-if="isLoggedIn && (latest || unread)" placement="bottom" :width="320" trigger="click">
    <template #reference>
      <el-badge :value="unread" :hidden="!unread" class="settle-badge">
        <el-button circle size="small" aria-label="竞猜结算通知">
          <span>🎯</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="latest" class="settle-pop">
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
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
    <div v-else class="settle-pop">
      <p>你有 {{ unread }} 条未读结算通知</p>
      <el-button link size="small" @click="$router.push('/me')">去球迷中心查看</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { markPredictRead, predictNotify } from '../stores/headerNotificationsStore'
import { isLoggedIn, fetchMe } from '../stores/authStore'

const router = useRouter()
const unread = computed(() => predictNotify.unread)
const latest = computed(() => predictNotify.latest)

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
</style>
