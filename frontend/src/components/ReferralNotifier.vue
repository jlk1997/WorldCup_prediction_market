<template>
  <el-popover v-if="isLoggedIn && (latest || unread)" placement="bottom" :width="320" trigger="click">
    <template #reference>
      <el-badge :value="unread" :hidden="!unread" class="ref-badge">
        <el-button circle size="small" aria-label="召友奖励">
          <span>🤝</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="latest" class="ref-pop">
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
      <el-button type="primary" size="small" @click="goAction">查看详情</el-button>
      <el-button link size="small" @click="markRead">知道了</el-button>
    </div>
    <div v-else class="ref-pop">
      <p>你有 {{ unread }} 条召友奖励通知</p>
      <el-button link size="small" @click="$router.push('/invite')">去召友中心</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  markReferralRead,
  referralNotify,
} from '../stores/headerNotificationsStore'
import { isLoggedIn } from '../stores/authStore'

const router = useRouter()
const unread = computed(() => referralNotify.unread)
const latest = computed(() => referralNotify.latest)

async function markRead() {
  await markReferralRead()
}

function goAction() {
  const action = (latest.value?.payload?.action as string) || '/invite'
  markRead()
  router.push(action)
}
</script>

<style scoped>
.ref-badge {
  margin-right: 4px;
}
.ref-pop p {
  margin: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wc-text-muted, #9a94a8);
}
</style>
