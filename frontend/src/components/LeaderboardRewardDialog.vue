<template>
  <el-dialog
    v-model="visible"
    :width="isMobile ? 'min(440px, 94vw)' : '520px'"
    align-center
    append-to-body
    :show-close="true"
    :close-on-click-modal="false"
    class="leaderboard-reward-dialog"
    @closed="onClosed"
  >
    <template #header>
      <div class="dialog-head">
        <div class="trophy-glow" aria-hidden="true">🏆</div>
        <div>
          <span class="head-badge">世界杯赛后福利</span>
          <h3 class="dialog-title">冲榜有礼 · 赛季虚拟荣誉</h3>
          <p class="dialog-sub">2026 世界杯结束后，排行榜上榜用户将获得站内虚拟奖励</p>
        </div>
      </div>
    </template>

    <div class="reward-body">
      <p class="lead">
        在「最后一舞」各榜<strong>成功上榜</strong>的球迷，赛后将统一发放<strong>虚拟礼包</strong>（球迷币、可用积分、专属装扮等），排名越高奖励越丰厚。
      </p>

      <div class="gift-grid">
        <div v-for="item in gifts" :key="item.title" class="gift-card">
          <span class="gift-icon" aria-hidden="true">{{ item.icon }}</span>
          <strong>{{ item.title }}</strong>
          <span class="gift-desc">{{ item.desc }}</span>
        </div>
      </div>

      <ul class="rule-list">
        <li>覆盖<strong>累计积分、可用积分、竞猜准度、军团榜</strong>等主流榜单</li>
        <li>奖励均为<strong>站内虚拟物品</strong>（球迷币 / 积分 / 装扮），不可提现、不含实物</li>
        <li>具体档位以赛后站内公告为准，请以官方通知为最终依据</li>
      </ul>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <label class="dismiss-row" :class="{ checked: skipToday }">
          <el-checkbox v-model="skipToday">今日不再显示</el-checkbox>
        </label>

        <div v-if="sharePanelOpen" class="share-panel">
          <p class="share-panel-title">分享排行榜 · 邀好友一起冲榜</p>
          <p class="share-panel-hint">链接带预览卡片，适合发微信好友或群</p>
          <textarea
            ref="shareTextRef"
            class="share-textarea"
            readonly
            rows="3"
            :value="shareText"
            @focus="selectShareText"
            @click="selectShareText"
          />
          <div class="share-panel-actions">
            <el-button
              type="primary"
              plain
              class="share-copy-btn"
              :loading="shareLoading"
              @click="copyShare"
            >
              {{ shareCopied ? '已复制，去粘贴分享' : '复制分享文案' }}
            </el-button>
            <el-button
              v-if="canNativeShare"
              plain
              class="share-native-btn"
              :disabled="shareLoading"
              @click="nativeShare"
            >
              唤起分享
            </el-button>
          </div>
        </div>

        <el-button
          plain
          class="share-btn"
          :class="{ active: sharePanelOpen }"
          @click="openSharePanel"
        >
          {{ sharePanelOpen ? '收起分享' : '晒排名链接' }}
        </el-button>
        <el-button type="primary" class="confirm-btn" @click="confirm">
          我知道了，冲榜去
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useBreakpoint } from '../composables/useBreakpoint'
import { dismissLeaderboardRewardForToday } from '../utils/leaderboardRewardPrompt'
import { copyToClipboard } from '../utils/copyToClipboard'
import { authState } from '../stores/authStore'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const { isMobile } = useBreakpoint()
const visible = ref(props.modelValue)
const skipToday = ref(false)
const sharePanelOpen = ref(false)
const shareLoading = ref(false)
const shareCopied = ref(false)
const shareTextRef = ref<HTMLTextAreaElement | null>(null)

const gifts = [
  { icon: '🪙', title: '球迷币礼包', desc: '上榜档位对应不同数量' },
  { icon: '✨', title: '可用积分', desc: '兑换头像框与主题' },
  { icon: '🏅', title: '专属装扮', desc: '赛季限定虚拟外观' },
  { icon: '🎖️', title: '荣誉徽章', desc: '名片与排行榜展示' },
]

const rankShareUrl = computed(() => {
  const site = (import.meta.env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')
  return `${site}/share/rank?period=season`
})

const shareText = computed(() => {
  const nick = authState.user?.nickname || '我'
  return `${nick} 正在「最后一舞」冲世界杯排行榜！一起来猜球冲榜\n${rankShareUrl.value}`
})

const canNativeShare = computed(
  () => typeof navigator !== 'undefined' && typeof navigator.share === 'function',
)

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
  },
)

watch(visible, (v) => {
  emit('update:modelValue', v)
  if (!v) {
    sharePanelOpen.value = false
    shareCopied.value = false
  }
})

function confirm() {
  if (skipToday.value) {
    dismissLeaderboardRewardForToday()
  }
  visible.value = false
}

async function openSharePanel() {
  if (sharePanelOpen.value) {
    sharePanelOpen.value = false
    return
  }
  sharePanelOpen.value = true
  shareCopied.value = false
  await nextTick()
  await copyShare()
}

function selectShareText() {
  const el = shareTextRef.value
  if (!el) return
  el.focus()
  el.select()
  try {
    el.setSelectionRange(0, el.value.length)
  } catch {
    /* ignore */
  }
}

async function copyShare() {
  shareLoading.value = true
  try {
    await nextTick()
    selectShareText()
    let ok = false
    try {
      ok = document.execCommand('copy')
    } catch {
      ok = false
    }
    if (!ok) {
      ok = await copyToClipboard(shareText.value)
    }
    if (ok) {
      shareCopied.value = true
      ElMessage.success({
        message: '分享文案已复制，去微信粘贴即可',
        duration: 2800,
        showClose: true,
      })
    } else {
      ElMessage.warning({
        message: '无法自动复制，请长按上方灰框内文字手动复制',
        duration: 5000,
        showClose: true,
      })
    }
  } finally {
    shareLoading.value = false
  }
}

async function nativeShare() {
  if (!canNativeShare.value) return
  shareLoading.value = true
  try {
    await navigator.share({
      title: '最后一舞 · 排行榜',
      text: `${authState.user?.nickname || '我'} 正在冲榜，一起来猜世界杯！`,
      url: rankShareUrl.value,
    })
    ElMessage.success('已唤起系统分享')
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      await copyShare()
    }
  } finally {
    shareLoading.value = false
  }
}

function onClosed() {
  if (skipToday.value) {
    dismissLeaderboardRewardForToday()
  }
  skipToday.value = false
  sharePanelOpen.value = false
  shareCopied.value = false
}
</script>

<style scoped>
.dialog-head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding-right: 28px;
}

.trophy-glow {
  font-size: 2.4rem;
  line-height: 1;
  filter: drop-shadow(0 0 14px rgba(212, 165, 116, 0.65));
  animation: trophy-pulse 2.4s ease-in-out infinite;
}

@keyframes trophy-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.08);
  }
}

.head-badge {
  display: inline-block;
  margin-bottom: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #1a1208;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 100%);
}

.dialog-title {
  margin: 0 0 6px;
  font-size: 1.15rem;
  font-weight: 900;
  font-family: var(--wc-font-serif);
  line-height: 1.35;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 55%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.dialog-sub {
  margin: 0;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.68);
  line-height: 1.45;
}

.reward-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.lead {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.82);
}

.lead strong {
  color: var(--wc-accent-gold);
}

.gift-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.gift-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 12px 10px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.22);
  background: rgba(10, 12, 24, 0.55);
}

.gift-icon {
  font-size: 1.45rem;
  line-height: 1;
}

.gift-card strong {
  font-size: 0.88rem;
  color: #f0d9b5;
}

.gift-desc {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.35;
}

.rule-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.58);
  line-height: 1.6;
}

.rule-list strong {
  color: rgba(240, 217, 181, 0.92);
  font-weight: 600;
}

.dialog-footer {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  width: 100%;
}

.dismiss-row {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.15);
  cursor: pointer;
}

.dismiss-row.checked {
  border-color: rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.08);
}

.share-panel {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(10, 12, 24, 0.75);
  animation: share-panel-in 0.22s ease;
}

@keyframes share-panel-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.share-panel-title {
  margin: 0 0 4px;
  font-size: 0.88rem;
  font-weight: 700;
  color: #f0d9b5;
}

.share-panel-hint {
  margin: 0 0 10px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
}

.share-textarea {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.35);
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.8rem;
  line-height: 1.5;
  resize: none;
  font-family: inherit;
  -webkit-user-select: all;
  user-select: all;
}

.share-textarea:focus {
  outline: none;
  border-color: rgba(212, 165, 116, 0.5);
  box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.15);
}

.share-panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.share-copy-btn,
.share-native-btn {
  flex: 1;
  min-height: 40px;
  min-width: 0;
}

.share-btn {
  width: 100%;
  min-height: 44px;
  font-weight: 700;
  border-color: rgba(212, 165, 116, 0.45);
  color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.08);
}

.share-btn.active {
  border-color: rgba(212, 165, 116, 0.65);
  background: rgba(212, 165, 116, 0.16);
}

.confirm-btn {
  width: 100%;
  min-height: 44px;
  font-weight: 800;
  border: none;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, #c9788a 100%);
  color: #1a1208;
}

.confirm-btn:hover {
  filter: brightness(1.05);
}

@media (max-width: 480px) {
  .gift-grid {
    grid-template-columns: 1fr;
  }

  .share-panel-actions {
    flex-direction: column;
  }
}
</style>

<style>
.leaderboard-reward-dialog.el-dialog {
  border-radius: 16px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: linear-gradient(165deg, rgba(28, 22, 36, 0.98) 0%, rgba(18, 14, 24, 0.99) 100%);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.55), 0 0 40px rgba(212, 165, 116, 0.12);
}

.leaderboard-reward-dialog .el-dialog__header {
  padding: 18px 20px 8px;
  margin-right: 0;
}

.leaderboard-reward-dialog .el-dialog__body {
  padding: 8px 20px 4px;
}

.leaderboard-reward-dialog .el-dialog__footer {
  padding: 8px 20px 18px;
}

.leaderboard-reward-dialog .el-dialog__headerbtn {
  top: 14px;
  right: 12px;
}

.leaderboard-reward-dialog .el-dialog__headerbtn .el-dialog__close {
  color: rgba(255, 255, 255, 0.55);
}

.leaderboard-reward-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: var(--wc-accent-gold);
}

.leaderboard-reward-dialog .el-dialog__footer .el-button {
  pointer-events: auto;
}
</style>
