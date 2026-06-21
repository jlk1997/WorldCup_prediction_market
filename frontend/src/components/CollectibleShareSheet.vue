<template>
  <component
    :is="isMobile ? ElDrawer : ElDialog"
    v-model="sheetOpen"
    :title="isMobile ? undefined : '分享卡牌'"
    direction="btt"
    :size="isMobile ? '88%' : undefined"
    :width="isMobile ? undefined : '440px'"
    class="collectible-share-sheet"
    @closed="closeShareSheet"
  >
    <template v-if="isMobile" #header>
      <span class="sheet-title">分享卡牌</span>
    </template>

    <div v-loading="loading || posterLoading" class="sheet-body">
      <p class="share-steps">① 保存海报 → ② 发微信好友/群 → ③ 好友扫码查看藏品</p>
      <p class="lead">复制文案或保存海报，展示你的球星数字藏品（虚拟收藏，仅供炫耀）。</p>

      <el-alert
        v-if="wechatHint"
        type="info"
        :closable="false"
        show-icon
        class="wechat-hint"
        title="微信内：保存海报后长按图片，发送到群聊或好友"
      />

      <textarea
        ref="textRef"
        class="share-text"
        readonly
        rows="4"
        :value="shareText"
        @focus="selectAll"
      />

      <div v-if="posterPreviewUrl" class="poster-preview">
        <img :src="posterPreviewUrl" alt="卡牌分享海报" />
      </div>

      <el-button type="primary" size="large" class="main-btn" @click="shareNative">
        分享给好友
      </el-button>

      <div class="sub-actions">
        <el-button plain @click="copyShareText">复制文案</el-button>
        <el-button plain @click="copyLink">复制链接</el-button>
        <el-button plain @click="savePoster">保存海报</el-button>
      </div>

      <p class="compliance">数字藏品为平台内虚拟收藏，无金钱价值，不可交易、不可转赠、不可提现。</p>
    </div>
  </component>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElDialog, ElDrawer } from 'element-plus'
import type { CollectibleCardBrief } from '@/api/collectible'
import { useBreakpoint } from '../composables/useBreakpoint'
import { useCollectibleShare } from '../composables/useCollectibleShare'
import { registerCollectibleShareSheet } from '../composables/useCollectibleShareSheet'
import { isWeChatBrowser } from '../utils/payEnv'

export interface CollectibleSharePayload {
  card: CollectibleCardBrief
  variant?: 'collectible' | 'set_complete'
  setName?: string
  subtitleOverride?: string
}

const { isMobile } = useBreakpoint()
const textRef = ref<HTMLTextAreaElement | null>(null)
const wechatHint = computed(() => isWeChatBrowser())

const {
  sheetOpen,
  loading,
  posterLoading,
  shareText,
  openShareSheet,
  closeShareSheet,
  copyShareText,
  copyLink,
  savePoster,
  shareNative,
  posterPreviewUrl,
} = useCollectibleShare()

function selectAll() {
  textRef.value?.select()
}

function show(payload: CollectibleSharePayload) {
  void openShareSheet(payload)
}

onMounted(() => {
  registerCollectibleShareSheet({ show })
})

onBeforeUnmount(() => {
  registerCollectibleShareSheet(null)
})

defineExpose({ show })
</script>

<style scoped>
.sheet-title {
  font-weight: 600;
  font-size: 1.05rem;
}
.sheet-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.share-steps {
  margin: 0;
  font-size: 0.82rem;
  color: var(--wc-accent-green, #3dd68c);
  line-height: 1.45;
}
.lead {
  margin: 0;
  font-size: 0.86rem;
  color: var(--wc-text-muted);
}
.wechat-hint {
  margin: 0;
}
.share-text {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.25);
  color: #f5f0e8;
  font-size: 0.85rem;
  line-height: 1.5;
  resize: none;
}
.poster-preview {
  text-align: center;
}
.poster-preview img {
  max-width: 100%;
  max-height: 340px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
}
.main-btn {
  width: 100%;
}
.sub-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.compliance {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  line-height: 1.45;
  text-align: center;
}
</style>
