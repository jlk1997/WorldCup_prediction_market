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
          <h3 class="dialog-title">冲榜有礼 · 神秘大礼等你来拿</h3>
          <p class="dialog-sub">2026 世界杯结束后，排行榜上榜用户均可获得惊喜回馈</p>
        </div>
      </div>
    </template>

    <div class="reward-body">
      <p class="lead">
        在「最后一舞」各榜<strong>成功上榜</strong>的球迷，赛后将统一发放神秘礼包，人人有份、排名越高惊喜越多！
      </p>

      <div class="gift-grid">
        <div v-for="item in gifts" :key="item.title" class="gift-card glass-inner">
          <span class="gift-icon" aria-hidden="true">{{ item.icon }}</span>
          <strong>{{ item.title }}</strong>
          <span class="gift-desc">{{ item.desc }}</span>
        </div>
      </div>

      <ul class="rule-list">
        <li>覆盖<strong>累计积分、可用积分、竞猜准度、军团榜</strong>等主流榜单</li>
        <li>实物类奖品以站内公告为准，颜色/尺码随机或按登记信息发放</li>
        <li>活动最终解释权归平台所有，请以赛后官方通知为准</li>
      </ul>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <label class="dismiss-row" :class="{ checked: skipToday }">
          <el-checkbox v-model="skipToday">今日不再显示</el-checkbox>
        </label>
        <el-button plain class="share-btn" @click="shareRank">晒排名链接</el-button>
        <el-button type="primary" class="confirm-btn" @click="confirm">
          我知道了，冲榜去
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useBreakpoint } from '../composables/useBreakpoint'
import { dismissLeaderboardRewardForToday } from '../utils/leaderboardRewardPrompt'
import { copyToClipboard } from '../utils/copyToClipboard'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const { isMobile } = useBreakpoint()
const visible = ref(props.modelValue)
const skipToday = ref(false)

const gifts = [
  { icon: '🪙', title: '金豆礼包', desc: '球迷币、积分加成' },
  { icon: '🏅', title: 'C罗 / 梅西手办', desc: '限量收藏款' },
  { icon: '👕', title: '正版球衣', desc: '国家队 / 俱乐部' },
  { icon: '🎁', title: '更多惊喜', desc: '神秘周边等你拆' },
]

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
  },
)

watch(visible, (v) => {
  emit('update:modelValue', v)
})

function confirm() {
  if (skipToday.value) {
    dismissLeaderboardRewardForToday()
  }
  visible.value = false
}

function shareRank() {
  const site = (import.meta.env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')
  const url = `${site}/share/rank?period=season`
  void copyToClipboard(url).then((ok) => {
    if (ok) ElMessage.success('排行榜分享链接已复制')
    else ElMessage.info(url)
  })
}

function onClosed() {
  if (skipToday.value) {
    dismissLeaderboardRewardForToday()
  }
  skipToday.value = false
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
  background: rgba(212, 165, 116, 0.06);
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
  gap: 12px;
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

.confirm-btn {
  width: 100%;
  min-height: 42px;
  font-weight: 800;
  border: none;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, #c9788a 100%);
  color: #1a1208;
}

.share-btn {
  width: 100%;
  min-height: 40px;
}

.confirm-btn:hover {
  filter: brightness(1.05);
}

@media (max-width: 480px) {
  .gift-grid {
    grid-template-columns: 1fr;
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
</style>
