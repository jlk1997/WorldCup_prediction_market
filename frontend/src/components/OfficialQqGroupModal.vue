<template>
  <el-dialog
    v-model="visible"
    width="92%"
    :style="{ maxWidth: '400px' }"
    align-center
    class="qq-group-dialog"
    :title="config.modal_title"
    @closed="onClosed"
  >
    <p class="modal-sub">{{ config.modal_subtitle }}</p>

    <div class="group-card">
      <div class="group-meta">
        <div class="group-avatar" aria-hidden="true">⚽</div>
        <div>
          <strong>{{ config.group_name }}</strong>
          <p>群号 {{ config.group_number }}</p>
        </div>
      </div>

      <div class="qr-wrap">
        <img :src="config.qr_image_url" :alt="`${config.group_name} QQ 群二维码`" class="qr-img" />
      </div>
      <p class="qr-hint">扫一扫二维码，加入群聊</p>
    </div>

    <ol v-if="config.steps?.length" class="steps">
      <li v-for="(s, i) in config.steps" :key="i">{{ s }}</li>
    </ol>

    <div class="actions">
      <el-button plain @click="copyGroupNo">复制群号</el-button>
      <el-button v-if="!isLoggedIn" type="primary" @click="goLogin">登录后领奖励</el-button>
      <el-button
        v-else-if="!claimed"
        type="primary"
        :loading="claiming"
        @click="onClaim"
      >
        我已加群，领取 +{{ config.reward_coins }} 球迷币
      </el-button>
      <el-button v-else type="success" disabled>已领取加群奖励</el-button>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { copyToClipboard } from '@/utils/copyToClipboard'
import { isLoggedIn, fetchMe } from '@/stores/authStore'
import {
  claimOfficialQqGroupReward,
  closeOfficialQqGroupModal,
  officialQqGroupConfig,
  officialQqGroupState,
} from '@/composables/useOfficialQqGroup'

const router = useRouter()
const route = useRoute()
const config = officialQqGroupConfig

const visible = computed({
  get: () => officialQqGroupState.modalOpen,
  set: (v: boolean) => {
    if (!v) closeOfficialQqGroupModal()
    else officialQqGroupState.modalOpen = v
  },
})

const claimed = computed(() => officialQqGroupState.claimed)
const claiming = computed(() => officialQqGroupState.claiming)

async function copyGroupNo() {
  const ok = await copyToClipboard(config.group_number)
  if (ok) ElMessage.success('群号已复制')
  else ElMessage.info(`群号：${config.group_number}`)
}

function goLogin() {
  closeOfficialQqGroupModal()
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

async function onClaim() {
  const res = await claimOfficialQqGroupReward()
  if (res.needLogin) {
    goLogin()
    return
  }
  if (res.ok) {
    await fetchMe()
    ElMessage.success(`已领取 ${res.coinsAdded} 球迷币，欢迎进群交流！`)
    window.dispatchEvent(new CustomEvent('daily-status-refresh'))
    return
  }
  if (officialQqGroupState.claimed) {
    ElMessage.info('你已经领过加群奖励啦')
  }
}

function onClosed() {
  const q = { ...route.query }
  if (q.qq) {
    delete q.qq
    router.replace({ path: route.path, query: q })
  }
}
</script>

<style scoped>
.modal-sub {
  margin: -8px 0 14px;
  font-size: 0.86rem;
  color: var(--wc-text-muted, #9a94a8);
  line-height: 1.55;
}

.group-card {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
}

.group-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  text-align: left;
}

.group-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  background: rgba(56, 189, 248, 0.15);
}

.group-meta strong {
  display: block;
  font-size: 1rem;
  color: #f5f0e8;
}

.group-meta p {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}

.qr-wrap {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

.qr-img {
  width: min(240px, 72vw);
  border-radius: 12px;
  background: #fff;
}

.qr-hint {
  margin: 8px 0 0;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}

.steps {
  margin: 14px 0 0;
  padding-left: 1.2rem;
  font-size: 0.82rem;
  color: #d0d7de;
  line-height: 1.65;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.actions .el-button {
  margin: 0;
  width: 100%;
}
</style>

<style>
.qq-group-dialog .el-dialog__header {
  padding-bottom: 4px;
}
.qq-group-dialog .el-dialog__title {
  font-weight: 800;
}
</style>
