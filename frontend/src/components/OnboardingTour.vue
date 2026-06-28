<template>
  <el-dialog
    v-model="visible"
    width="560px"
    align-center
    :show-close="true"
    :close-on-click-modal="false"
    :lock-scroll="false"
    class="onboarding-dialog"
    @closed="onDialogClosed"
  >
    <template #header>
      <div class="onboard-header">
        <span class="onboard-badge">首次使用 · 9 步指引</span>
        <h2 class="onboard-title">欢迎使用「最后一舞：世界杯2026」</h2>
        <p class="onboard-subtitle">带你快速上手赛事大屏、竞猜大厅与 AI 分析</p>
      </div>
    </template>

    <div class="onboard-body">
      <div class="step-track" role="tablist" aria-label="引导步骤">
        <button
          v-for="(s, i) in steps"
          :key="s.title"
          type="button"
          class="step-dot"
          :class="{ active: i === step, done: i < step }"
          :aria-label="`第 ${i + 1} 步：${s.title}`"
          @click="goStep(i)"
        >
          <span class="dot-num">{{ i + 1 }}</span>
          <span class="dot-label">{{ s.short }}</span>
        </button>
      </div>

      <div class="step-card glass-panel">
        <div class="step-icon-wrap" :style="{ '--accent': steps[step].color }">
          <el-icon :size="28"><component :is="steps[step].icon" /></el-icon>
        </div>
        <div class="step-text">
          <h3>{{ steps[step].title }}</h3>
          <p class="step-desc">{{ steps[step].desc }}</p>
          <ul class="step-tips">
            <li v-for="tip in steps[step].tips" :key="tip">{{ tip }}</li>
          </ul>
        </div>
      </div>

      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${((step + 1) / steps.length) * 100}%` }" />
      </div>
      <p class="progress-hint">第 {{ step + 1 }} / {{ steps.length }} 步</p>
    </div>

    <template #footer>
      <div class="onboard-footer">
        <el-button class="btn-ghost" text @click="skip">跳过引导</el-button>
        <div class="footer-actions">
          <el-button v-if="step > 0" class="btn-secondary" @click="prev">上一步</el-button>
          <el-button type="primary" class="btn-primary" @click="next">
            {{ step >= steps.length - 1 ? '开始使用' : '下一步' }}
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { DataBoard, Trophy, MagicStick, View, Share, Coin, Postcard, ShoppingCart } from '@element-plus/icons-vue'
import { trackEvent } from '@/utils/analytics'
import { fetchRecommendations, profileState } from '@/stores/profileStore'
import {
  GuidePriority,
  flushGuideQueue,
  notifyGuideClosed,
  notifyGuideOpened,
  registerGuide,
  unregisterGuide,
} from '@/composables/useGuideOrchestrator'
import { cleanupElementScrollLock } from '@/utils/scrollRoot'

const STORAGE_KEY = 'wc2026_onboarded'
const STEP_KEY = 'wc2026_tour_step'
const TOUR_ID = 'onboarding-tour'
const PREDICT_STEP_INDEX = 4
const router = useRouter()
const visible = ref(true)

function readStep() {
  const raw = sessionStorage.getItem(STEP_KEY)
  const n = raw ? Number.parseInt(raw, 10) : 0
  return Number.isFinite(n) && n >= 0 && n < 9 ? n : 0
}

const step = ref(readStep())

function saveStep(value: number) {
  sessionStorage.setItem(STEP_KEY, String(value))
}

interface TourStep {
  title: string
  short: string
  desc: string
  tips: string[]
  icon: Component
  color: string
}

const steps: TourStep[] = [
  {
    title: '赛事大屏',
    short: '大屏',
    desc: '首页聚焦当日关键比赛，实时比分与 AI 快览一目了然。',
    tips: ['焦点比赛卡片 + 胜率走势', '进行中比赛可一键赛中分析'],
    icon: DataBoard,
    color: '#D2A76D',
  },
  {
    title: '赛事中心',
    short: 'Live',
    desc: 'BSD 实时比分、104 场赛程与淘汰赛对阵由后台自动同步。',
    tips: ['Live / 赛程 / 淘汰赛 Tab 切换', '完赛后自动更新晋级对阵'],
    icon: Trophy,
    color: '#58a6ff',
  },
  {
    title: 'AI 多 Agent 工作台',
    short: 'AI',
    desc: 'News → Tactical → Predict → Critic 多步分析，支持流式进度。',
    tips: ['赛前 / 赛中 / 赛后三种模式', '历史记录可搜索、可筛选'],
    icon: MagicStick,
    color: '#a371f7',
  },
  {
    title: '3D 球场模式',
    short: '3D',
    desc: '右上角切换性能档位；分析时展示战术热力与进球特效。',
    tips: ['低配机可选「性能模式」', '大屏与 3D 背景可独立开关'],
    icon: View,
    color: '#3fb950',
  },
  {
    title: '竞猜大厅',
    short: '竞猜',
    desc: '每天 1 次免费竞猜，猜中得积分冲榜；质押球迷币可加码收益。',
    tips: ['选胜平负 → 勾选免费 → 提交', '赛后自动开奖，猜中有弹窗通知'],
    icon: Coin,
    color: '#e6a23c',
  },
  {
    title: '召友扩编',
    short: '召友',
    desc: '分享邀请链接，好友注册并完成档案，双方得球迷币与军团贡献。',
    tips: ['球迷中心 → 召友中心查看进度', '每周召友榜 Top10 有额外积分奖励'],
    icon: Share,
    color: '#f0a020',
  },
  {
    title: '卡牌中心',
    short: '卡牌',
    desc: '猜中得卡 → 快速匹配对决上分 · 文昌链凭证铸造。',
    tips: ['质押/对决/ Fantasy 用同一张卡', '积分二级交易，无 RMB 二级'],
    icon: Postcard,
    color: '#d4a574',
  },
  {
    title: '限量打新',
    short: '打新',
    desc: '人民币或球迷币首发限量球星卡，序列号稀缺；AI 顾问帮你参考值不值。',
    tips: ['实名 + 18+ 确认', '支付结果页可查看链上进度'],
    icon: ShoppingCart,
    color: '#58a6ff',
  },
  {
    title: '持卡 AI 折扣',
    short: '折扣',
    desc: '持有或质押相关球队卡，AI 分析费自动省 30%；商城可购分析次数包。',
    tips: ['竞猜大厅内嵌 AI 摘要', '一键跟 AI 选后再确认提交'],
    icon: MagicStick,
    color: '#a371f7',
  },
]

const routes = ['/', '/live', '/agent', '/', '/predict', '/invite', '/collection', '/mint', '/shop']

function finish() {
  sessionStorage.removeItem(STEP_KEY)
  localStorage.setItem(STORAGE_KEY, '1')
  trackEvent('tour_finish')
  notifyGuideClosed(TOUR_ID)
  cleanupElementScrollLock()
  flushGuideQueue()
}

function skip() {
  visible.value = false
  trackEvent('tour_skip', { step: step.value })
  finish()
}

async function navigateForStep(i: number) {
  const path = routes[i] || '/'
  if (i === PREDICT_STEP_INDEX) {
    visible.value = false
    await router.push(path)
    await nextTick()
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())))
    visible.value = true
    notifyGuideOpened(TOUR_ID, GuidePriority.OnboardingTour)
    return
  }
  await router.push(path)
}

function prev() {
  if (step.value > 0) {
    step.value -= 1
    saveStep(step.value)
    void navigateForStep(step.value)
  }
}

function goStep(i: number) {
  step.value = i
  saveStep(i)
  void navigateForStep(i)
}

function next() {
  if (step.value >= steps.length - 1) {
    visible.value = false
    finish()
    void goPredictAfterTour()
    return
  }
  step.value += 1
  saveStep(step.value)
  void navigateForStep(step.value)
}

async function goPredictAfterTour() {
  let path = '/predict'
  try {
    if (!profileState.recommendations) {
      await fetchRecommendations()
    }
    const mid = profileState.recommendations?.next_main_match?.id
    if (mid) path = `/predict?highlight=${mid}`
  } catch {
    /* optional */
  }
  router.push(path)
}

function onDialogClosed() {
  finish()
}

onMounted(() => {
  registerGuide(TOUR_ID, {
    priority: GuidePriority.OnboardingTour,
    isActive: () => visible.value,
    open: () => {
      visible.value = true
    },
  })
  notifyGuideOpened(TOUR_ID, GuidePriority.OnboardingTour)
  void navigateForStep(step.value)
})

onUnmounted(() => {
  unregisterGuide(TOUR_ID)
  notifyGuideClosed(TOUR_ID)
})
</script>

<style scoped>
.onboard-header {
  text-align: left;
  padding-right: 24px;
}

.onboard-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #D2A76D;
  background: rgba(210, 167, 109, 0.12);
  border: 1px solid rgba(210, 167, 109, 0.35);
  margin-bottom: 12px;
}

.onboard-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.35;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 45%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.onboard-subtitle {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.72);
}

.onboard-body {
  padding: 4px 0 0;
}

.step-track {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}

.step-dot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 4px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, transform 0.15s;
  color: rgba(255, 255, 255, 0.45);
}

.step-dot:hover {
  border-color: rgba(210, 167, 109, 0.35);
  background: rgba(210, 167, 109, 0.06);
}

.step-dot.active {
  border-color: rgba(210, 167, 109, 0.65);
  background: rgba(210, 167, 109, 0.12);
  color: #f0d9b5;
  transform: translateY(-1px);
}

.step-dot.done {
  color: rgba(255, 255, 255, 0.65);
}

.dot-num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.step-dot.active .dot-num {
  background: linear-gradient(135deg, #D2A76D, #A67C41);
  border-color: transparent;
  color: #1a1208;
}

.dot-label {
  font-size: 11px;
  font-weight: 600;
}

.step-card {
  display: flex;
  gap: 18px;
  padding: 22px 20px;
  border-radius: 16px;
  background: rgba(22, 27, 34, 0.92) !important;
  min-height: 168px;
}

.step-icon-wrap {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent, #D2A76D);
  background: color-mix(in srgb, var(--accent, #D2A76D) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent, #D2A76D) 35%, transparent);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.step-text h3 {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 700;
  color: #f0f3f6;
}

.step-desc {
  margin: 0 0 14px;
  font-size: 15px;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.88);
}

.step-tips {
  margin: 0;
  padding-left: 18px;
  list-style: none;
}

.step-tips li {
  position: relative;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.62);
  margin-bottom: 6px;
}

.step-tips li::before {
  content: '';
  position: absolute;
  left: -14px;
  top: 0.55em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #D2A76D;
  box-shadow: 0 0 8px rgba(210, 167, 109, 0.6);
}

.progress-bar {
  height: 4px;
  margin-top: 20px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #A67C41, #D2A76D, #f0d9b5);
  transition: width 0.35s ease;
}

.progress-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  text-align: right;
}

.onboard-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 12px;
}

.footer-actions {
  display: flex;
  gap: 10px;
}

.btn-primary {
  min-width: 108px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--wc-accent-gold-light) 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%) !important;
  border: none !important;
  color: #1a1208 !important;
}

.btn-primary:hover {
  filter: brightness(1.08);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.14) !important;
  color: rgba(255, 255, 255, 0.85) !important;
}

.btn-ghost {
  color: rgba(255, 255, 255, 0.5) !important;
}

.btn-ghost:hover {
  color: rgba(255, 255, 255, 0.85) !important;
}

@media (max-width: 520px) {
  .step-track {
    grid-template-columns: repeat(3, 1fr);
  }

  .step-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .onboard-footer {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .footer-actions {
    justify-content: stretch;
  }

  .footer-actions .el-button {
    flex: 1;
  }
}
</style>

<style>
/* Dialog teleports to body — global overrides */
.onboarding-dialog.el-dialog {
  background: linear-gradient(165deg, #141828 0%, #0f1224 48%, #07080f 100%) !important;
  border: 1px solid var(--wc-border-soft) !important;
  border-radius: 20px !important;
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.65),
    0 0 0 1px rgba(255, 255, 255, 0.04) inset,
    0 1px 0 rgba(210, 167, 109, 0.15) inset !important;
  overflow: hidden;
}

.onboarding-dialog .el-dialog__header {
  padding: 24px 24px 8px !important;
  margin-right: 0 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.onboarding-dialog .el-dialog__headerbtn {
  top: 18px;
  right: 18px;
  width: 36px;
  height: 36px;
}

.onboarding-dialog .el-dialog__headerbtn .el-dialog__close {
  color: rgba(255, 255, 255, 0.55) !important;
  font-size: 18px;
}

.onboarding-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: #D2A76D !important;
}

.onboarding-dialog .el-dialog__body {
  padding: 16px 24px 8px !important;
  color: #f0f3f6 !important;
}

.onboarding-dialog .el-dialog__footer {
  padding: 12px 24px 24px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.el-overlay:has(+ .onboarding-dialog),
.el-overlay-dialog:has(.onboarding-dialog) {
  backdrop-filter: blur(8px);
  background-color: rgba(0, 0, 0, 0.72) !important;
}

@media (max-width: 768px) {
  .onboarding-dialog.el-dialog {
    width: 92vw !important;
    max-width: 92vw !important;
    margin: 4vh auto !important;
    border-radius: 16px !important;
  }

  .onboarding-dialog .el-dialog__header,
  .onboarding-dialog .el-dialog__body,
  .onboarding-dialog .el-dialog__footer {
    padding-left: 16px !important;
    padding-right: 16px !important;
  }

  .onboard-title {
    font-size: 18px;
  }
}
</style>
