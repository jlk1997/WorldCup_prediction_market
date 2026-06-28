<template>
  <div v-if="visible" class="chain-alert-banner" :class="variant">
    <div class="banner-copy">
      <span class="banner-icon">{{ variant === 'failed' ? '⚠️' : '⏳' }}</span>
      <div>
        <strong>{{ title }}</strong>
        <p>{{ subtitle }}</p>
      </div>
    </div>
    <el-button v-if="variant === 'failed'" size="small" type="warning" plain :loading="retrying" @click="onRetry">
      重试铸造
    </el-button>
    <el-button v-else size="small" plain @click="goCollection">查看进度</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { retryCollectibleChainMint } from '@/api/collectible'
import { extractApiError } from '@/utils/apiError'

const props = defineProps<{
  failedCount?: number
  pendingCount?: number
  firstFailedUserCardId?: number | null
}>()

const emit = defineEmits<{ retried: [] }>()

const router = useRouter()
const retrying = ref(false)

const variant = computed(() => (props.failedCount && props.failedCount > 0 ? 'failed' : 'pending'))

const visible = computed(
  () =>
    (props.failedCount && props.failedCount > 0) || (props.pendingCount && props.pendingCount > 0),
)

const title = computed(() =>
  variant.value === 'failed'
    ? `${props.failedCount} 张链上铸造失败`
    : `${props.pendingCount} 张正在链上铸造`,
)

const subtitle = computed(() =>
  variant.value === 'failed'
    ? '支付已成功，可一键重新排队，通常数分钟内完成'
    : '可在收藏册查看铸造进度',
)

function goCollection() {
  router.push('/collection')
}

async function onRetry() {
  const id = props.firstFailedUserCardId
  if (!id) {
    goCollection()
    return
  }
  retrying.value = true
  try {
    await retryCollectibleChainMint(id)
    ElMessage.success('已重新提交链上铸造')
    emit('retried')
  } catch (e) {
    ElMessage.error(extractApiError(e, '重试失败，请稍后再试'))
  } finally {
    retrying.value = false
  }
}
</script>

<style scoped>
.chain-alert-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 10px 0;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.25);
  background: rgba(212, 165, 116, 0.08);
}
.chain-alert-banner.failed {
  border-color: rgba(245, 166, 35, 0.45);
  background: rgba(245, 166, 35, 0.1);
}
.banner-copy {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  flex: 1;
  min-width: 0;
}
.banner-copy strong {
  display: block;
  font-size: 0.88rem;
}
.banner-copy p {
  margin: 4px 0 0;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
}
.banner-icon {
  font-size: 1.1rem;
  line-height: 1;
}
</style>
