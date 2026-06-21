<template>
  <component
    :is="isMobile ? ElDrawer : ElDialog"
    v-model="sheetOpen"
    :title="isMobile ? undefined : '分享给好友'"
    direction="btt"
    :size="isMobile ? '85%' : undefined"
    :width="isMobile ? undefined : '420px'"
    class="invite-share-sheet"
    @closed="closeShareSheet"
  >
    <template v-if="isMobile" #header>
      <span class="sheet-title">分享给好友</span>
    </template>

    <div v-loading="loading || posterLoading" class="sheet-body">
      <p class="share-steps">① 保存海报 → ② 发微信好友/群 → ③ 好友扫码注册（双方得币）</p>
      <p class="benefit-line">好友注册得 100 球迷币 · 你获有效邀请奖励 · AI 快览 + 猜中掉落数字藏品</p>
      <p v-if="benefitLine" class="tier-line">{{ benefitLine }}</p>

      <el-alert
        v-if="wechatHint"
        type="info"
        :closable="false"
        show-icon
        class="wechat-hint"
        title="微信内分享：保存海报后长按图片，发送到群聊或好友"
      />

      <div v-if="posterPreviewUrl" class="poster-preview">
        <img :src="posterPreviewUrl" alt="分享海报预览" />
      </div>

      <el-button type="primary" size="large" class="main-btn" @click="shareInvite">
        分享给好友
      </el-button>

      <div class="sub-actions">
        <el-button plain @click="copyInviteLink">复制链接</el-button>
        <el-button plain @click="saveInvitePoster">保存海报</el-button>
        <el-button plain @click="copyInviteCode">复制邀请码</el-button>
      </div>

      <p class="code-hint">邀请码：{{ cachedMe?.invite_code || '—' }}</p>

      <router-link to="/invite" class="hub-link" @click="closeShareSheet">
        查看召友规则与好友进度 →
      </router-link>
    </div>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElDialog, ElDrawer } from 'element-plus'
import { useBreakpoint } from '../composables/useBreakpoint'
import { useInviteShare } from '../composables/useInviteShare'
import { isWeChatBrowser } from '../utils/payEnv'

const { isMobile } = useBreakpoint()
const {
  sheetOpen,
  loading,
  posterLoading,
  cachedMe,
  posterPreviewUrl,
  shareInvite,
  copyInviteLink,
  copyInviteCode,
  saveInvitePoster,
  closeShareSheet,
} = useInviteShare()

const wechatHint = computed(() => isWeChatBrowser())

const benefitLine = computed(() => {
  const me = cachedMe.value
  if (!me) return null
  if (me.next_tier) {
    return `再邀 ${me.next_tier.remaining} 位有效好友，解锁「${me.next_tier.title}」`
  }
  return `有效邀请 ${me.effective_invites} 人 · 本季已赚 ${me.season_coins_earned} 球迷币`
})
</script>

<style scoped>
.sheet-title {
  font-weight: 700;
  color: #f5f0e8;
}

.sheet-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 0 4px 12px;
}

.share-steps {
  margin: 0;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.25);
  font-size: 0.82rem;
  color: #8fd48a;
  text-align: center;
  line-height: 1.45;
}

.benefit-line {
  margin: 0;
  font-size: 0.88rem;
  color: var(--wc-accent-gold);
  text-align: center;
  line-height: 1.5;
}

.tier-line {
  margin: 0;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  text-align: center;
}

.wechat-hint {
  margin: 0;
}

.poster-preview {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

.poster-preview img {
  max-width: 260px;
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
}

.main-btn {
  width: 100%;
  min-height: 48px;
  font-weight: 700;
}

.sub-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.sub-actions .el-button {
  flex: 1;
  min-width: 100px;
}

.code-hint {
  margin: 0;
  text-align: center;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}

.hub-link {
  display: block;
  text-align: center;
  font-size: 0.82rem;
  color: var(--wc-accent-gold);
  text-decoration: none;
}

.hub-link:hover {
  text-decoration: underline;
}
</style>
