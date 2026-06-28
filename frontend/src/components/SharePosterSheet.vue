<template>
  <el-dialog v-model="visible" title="分享海报" width="92%" align-center class="share-poster-dialog">
    <div class="poster" :class="variant">
      <p class="brand">最后一舞 · 世界杯2026</p>
      <h3>{{ title }}</h3>
      <p class="subtitle">{{ subtitle }}</p>
      <p v-if="extra" class="extra">{{ extra }}</p>
      <p class="disclaimer">{{ disclaimer }}</p>
    </div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" @click="copyText">复制文案</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { copyToClipboard } from '@/utils/copyToClipboard'
import { registerSharePosterSheet, type SharePosterPayload } from '@/composables/useSharePoster'
import { trackEvent } from '@/utils/analytics'

const visible = ref(false)
const title = ref('')
const subtitle = ref('')
const extra = ref('')
const variant = ref<'ai' | 'chain'>('ai')
const disclaimer = 'AI/链信息仅供参考 · 虚拟藏品无现金价值'

function show(opts: SharePosterPayload) {
  variant.value = opts.variant || 'ai'
  title.value = opts.title
  subtitle.value = opts.subtitle
  extra.value = opts.extra || ''
  visible.value = true
  trackEvent('share_poster_open', { variant: variant.value })
}

async function copyText() {
  const text = [title.value, subtitle.value, extra.value, disclaimer].filter(Boolean).join('\n')
  const ok = await copyToClipboard(text)
  ElMessage[ok ? 'success' : 'warning'](ok ? '已复制分享文案' : '复制失败，请手动复制')
  if (ok) trackEvent('share_poster_copy', { variant: variant.value })
}

onMounted(() => registerSharePosterSheet({ show }))
onUnmounted(() => registerSharePosterSheet(null))

defineExpose({ show })
</script>

<style scoped>
.poster {
  padding: 20px;
  border-radius: 12px;
  background: linear-gradient(145deg, #12141f, #1a1228);
  color: #eee;
  text-align: center;
}
.poster.chain {
  border: 1px solid rgba(212, 165, 116, 0.45);
}
.brand {
  font-size: 0.72rem;
  color: #d4a574;
  margin: 0 0 8px;
}
h3 {
  margin: 0 0 8px;
  font-size: 1.1rem;
}
.subtitle {
  margin: 0 0 6px;
  font-size: 0.9rem;
  color: #ccc;
}
.extra {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: #a371f7;
}
.disclaimer {
  margin: 12px 0 0;
  font-size: 0.68rem;
  color: #888;
}
</style>
