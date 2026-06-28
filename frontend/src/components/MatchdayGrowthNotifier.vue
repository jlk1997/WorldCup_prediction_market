<template>
  <el-popover v-if="isLoggedIn && (latest || unread)" placement="bottom" :width="340" trigger="click">
    <template #reference>
      <el-badge :value="unread" :hidden="!unread" class="growth-badge">
        <el-button circle size="small" aria-label="比赛日与成长通知">
          <span>🏟️</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="latest" class="growth-pop">
      <span class="cat-tag">{{ categoryLabel(latest.category) }}</span>
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
      <div class="pop-actions">
        <el-button type="primary" size="small" @click="goAction">去看看</el-button>
        <el-button link size="small" @click="markRead">知道了</el-button>
      </div>
    </div>
    <div v-else class="growth-pop">
      <p>你有 {{ unread }} 条未读提醒</p>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { growthNotify, markGrowthRead } from '@/stores/headerNotificationsStore'
import { isLoggedIn } from '@/stores/authStore'

const router = useRouter()
const unread = computed(() => growthNotify.unread)
const latest = computed(() => growthNotify.latest)

function categoryLabel(cat: string) {
  const map: Record<string, string> = {
    matchday_repurchase: '比赛日',
    matchday_ai: 'AI 更新',
    fantasy_weekly: 'Fantasy',
  }
  return map[cat] || '提醒'
}

async function markRead() {
  await markGrowthRead()
}

function goAction() {
  const payload = latest.value?.payload as Record<string, unknown> | undefined
  const path = String(payload?.path || payload?.action || '/')
  markRead()
  router.push(path)
}
</script>

<style scoped>
.growth-badge {
  margin-right: 4px;
}
.growth-pop .cat-tag {
  display: inline-block;
  margin-bottom: 6px;
  font-size: 0.65rem;
  color: var(--wc-accent-gold);
  letter-spacing: 0.04em;
}
.growth-pop p {
  margin: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wc-text-muted);
}
.pop-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
