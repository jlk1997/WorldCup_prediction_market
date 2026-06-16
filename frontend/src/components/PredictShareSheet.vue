<template>
  <el-dialog
    v-model="open"
    title="晒一下你的预测"
    width="min(420px, 92vw)"
    align-center
    append-to-body
    class="predict-share-dialog"
    @closed="onClosed"
  >
    <p class="lead">复制文案或保存海报，发给球友一起猜这场。</p>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="wechat-tip"
      title="微信里：先保存海报，再长按图片发到群聊"
    />
    <textarea ref="textRef" class="share-text" readonly rows="4" :value="shareText" @focus="selectAll" />
    <div v-if="posterUrl" class="poster-wrap">
      <img :src="posterUrl" alt="预测分享海报" class="poster-img" />
    </div>
    <div class="actions">
      <el-button type="primary" plain :loading="copying" @click="copyText">
        {{ copied ? '已复制' : '复制文案' }}
      </el-button>
      <el-button plain :loading="posterLoading" @click="savePoster">保存海报</el-button>
      <el-button v-if="canNativeShare" plain @click="nativeShare">唤起分享</el-button>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { registerPredictShareSheet } from '@/composables/usePredictShareSheet'
import { ElMessage } from 'element-plus'
import { copyToClipboard } from '@/utils/copyToClipboard'
import { downloadSharePoster, generateSharePosterObjectUrl } from '@/utils/sharePoster'
import { posterDisplayName } from '@/utils/sharePosterDisplayName'
import { trackEvent } from '@/utils/analytics'

export interface PredictSharePayload {
  team1: string
  team2: string
  pickLabel: string
  shareUrl: string
  nickname?: string
}

const open = ref(false)
const payload = ref<PredictSharePayload | null>(null)
const copying = ref(false)
const copied = ref(false)
const posterLoading = ref(false)
const posterUrl = ref<string | null>(null)
const textRef = ref<HTMLTextAreaElement | null>(null)

const shareText = computed(() => {
  const p = payload.value
  if (!p) return ''
  const nick = p.nickname || '我'
  return `${nick} 押了 ${p.team1} vs ${p.team2} · ${p.pickLabel}\n${p.shareUrl}`
})

const canNativeShare = computed(
  () => typeof navigator !== 'undefined' && typeof navigator.share === 'function',
)

function selectAll() {
  textRef.value?.select()
}

async function refreshPoster() {
  const p = payload.value
  if (!p) return
  if (posterUrl.value) {
    URL.revokeObjectURL(posterUrl.value)
    posterUrl.value = null
  }
  posterLoading.value = true
  try {
    posterUrl.value = await generateSharePosterObjectUrl({
      variant: 'predict',
      displayName: posterDisplayName(p.nickname),
      title: `${p.team1} vs ${p.team2}`,
      subtitle: `${posterDisplayName(p.nickname)} 已下注 · 你也来猜胜负？`,
      pickHighlight: p.pickLabel,
      statsLine: '猜中拿积分 · 可换装扮',
      footer: '娱乐竞猜 · 非博彩 · 最后一舞',
      qrUrl: p.shareUrl,
    })
  } finally {
    posterLoading.value = false
  }
}

function show(data: PredictSharePayload) {
  payload.value = data
  copied.value = false
  open.value = true
  trackEvent('predict_share_sheet_open')
  void refreshPoster()
}

async function copyText() {
  copying.value = true
  try {
    const ok = await copyToClipboard(shareText.value)
    copied.value = ok
    if (ok) ElMessage.success('文案已复制')
    else {
      selectAll()
      ElMessage.info('请手动复制上方文案')
    }
    trackEvent('predict_share_copy')
  } finally {
    copying.value = false
  }
}

async function savePoster() {
  const p = payload.value
  if (!p) return
  posterLoading.value = true
  try {
    await downloadSharePoster(
      {
        variant: 'predict',
        displayName: posterDisplayName(p.nickname),
        title: `${p.team1} vs ${p.team2}`,
        subtitle: `${posterDisplayName(p.nickname)} 已下注 · 你也来猜胜负？`,
        pickHighlight: p.pickLabel,
        statsLine: '猜中拿积分 · 可换装扮',
        footer: '娱乐竞猜 · 非博彩 · 最后一舞',
        qrUrl: p.shareUrl,
      },
      'wc2026-predict.png',
    )
    ElMessage.success('海报已保存')
    trackEvent('predict_share_poster_save')
  } catch {
    ElMessage.error('海报生成失败')
  } finally {
    posterLoading.value = false
  }
}

async function nativeShare() {
  const p = payload.value
  if (!p || !canNativeShare.value) return
  try {
    await navigator.share({ title: '我的世界杯预测', text: shareText.value, url: p.shareUrl })
  } catch {
    /* cancelled */
  }
}

function onClosed() {
  if (posterUrl.value) {
    URL.revokeObjectURL(posterUrl.value)
    posterUrl.value = null
  }
  payload.value = null
}

watch(open, (v) => {
  if (!v) onClosed()
})

onMounted(() => {
  registerPredictShareSheet({ show })
})

onBeforeUnmount(() => {
  registerPredictShareSheet(null)
})

defineExpose({ show })
</script>

<style scoped>
.lead {
  margin: 0 0 8px;
  font-size: 0.88rem;
  color: var(--wc-text-muted);
}
.wechat-tip {
  margin: 0 0 12px;
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
.poster-wrap {
  margin-top: 12px;
  text-align: center;
}
.poster-img {
  max-width: 100%;
  max-height: 320px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
  justify-content: center;
}
</style>
