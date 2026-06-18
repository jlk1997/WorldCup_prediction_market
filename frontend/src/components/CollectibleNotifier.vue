<template>
  <el-popover v-if="isLoggedIn && (latest || unread)" placement="bottom" :width="320" trigger="click">
    <template #reference>
      <el-badge :value="unread" :hidden="!unread" class="collectible-badge">
        <el-button circle size="small" aria-label="收藏通知">
          <span>🃏</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="latest" class="collectible-pop">
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
      <el-button type="primary" size="small" @click="goCollection">查看收藏册</el-button>
      <el-button link size="small" @click="markRead">知道了</el-button>
    </div>
    <div v-else class="collectible-pop">
      <p>你有 {{ unread }} 条收藏通知</p>
      <el-button link size="small" @click="$router.push('/collection')">去收藏册</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { markCollectibleRead, collectibleNotify } from '@/stores/headerNotificationsStore'
import { isLoggedIn } from '@/stores/authStore'
import { openCollectibleReveal } from '@/stores/collectibleRevealStore'
import type { CollectibleDropResult } from '@/api/collectible'

const router = useRouter()
const unread = computed(() => collectibleNotify.unread)
const latest = computed(() => collectibleNotify.latest)

async function markRead() {
  await markCollectibleRead()
}

function goCollection() {
  const payload = latest.value?.payload as Record<string, unknown> | undefined
  const drop = payload?.collectible_drop as CollectibleDropResult | undefined
  markRead()
  if (drop?.dropped) {
    openCollectibleReveal(drop, { subtitle: String(latest.value?.title || '') })
  } else {
    router.push(String(payload?.action || '/collection'))
  }
}
</script>

<style scoped>
.collectible-badge {
  margin-right: 4px;
}
.collectible-pop p {
  margin: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wc-text-muted, #9a94a8);
}
</style>
