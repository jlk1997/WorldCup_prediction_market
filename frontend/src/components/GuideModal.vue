<template>
  <el-dialog
    v-model="visible"
    width="560px"
    align-center
    :show-close="true"
    :close-on-click-modal="false"
    class="guide-modal-dialog"
    @closed="onClosed"
  >
    <template v-if="cfg" #header>
      <div class="guide-header">
        <span v-if="cfg.dialog.badge" class="guide-badge">{{ cfg.dialog.badge }}</span>
        <h2 class="guide-title">{{ cfg.dialog.title }}</h2>
        <p v-if="cfg.dialog.subtitle" class="guide-subtitle">{{ cfg.dialog.subtitle }}</p>
      </div>
    </template>

    <div v-if="cfg" class="guide-body">
      <div class="step-track" role="tablist">
        <button
          v-for="(s, i) in cfg.steps"
          :key="s.title"
          type="button"
          class="step-dot"
          :class="{ active: i === step, done: i < step }"
          @click="step = i"
        >
          <span class="dot-num">{{ i + 1 }}</span>
          <span class="dot-label">{{ s.icon || i + 1 }}</span>
        </button>
      </div>

      <div class="step-card glass-panel">
        <div v-if="current?.icon" class="step-icon">{{ current.icon }}</div>
        <div class="step-text">
          <h3>{{ current?.title }}</h3>
          <p v-if="current?.desc" class="step-desc">{{ current.desc }}</p>
          <p v-if="current?.highlight" class="step-highlight">{{ current.highlight }}</p>
          <ul v-if="current?.bullets?.length" class="step-bullets">
            <li v-for="b in current.bullets" :key="b">{{ b }}</li>
          </ul>
        </div>
      </div>

      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${((step + 1) / cfg.steps.length) * 100}%` }" />
      </div>
      <p class="progress-hint">第 {{ step + 1 }} / {{ cfg.steps.length }} 步</p>
    </div>

    <template v-if="cfg" #footer>
      <div class="guide-footer">
        <el-button text @click="skip">{{ cfg.footer.skip || '跳过' }}</el-button>
        <div class="footer-actions">
          <el-button v-if="step > 0" @click="step -= 1">{{ cfg.footer.prev || '上一步' }}</el-button>
          <el-button v-if="!isLast" type="primary" @click="step += 1">
            {{ cfg.footer.next || '下一步' }}
          </el-button>
          <template v-else>
            <el-button
              v-if="cfg.footer.secondary_finish && cfg.finish_action?.secondary_route"
              plain
              @click="finish(cfg.finish_action.secondary_route)"
            >
              {{ cfg.footer.secondary_finish }}
            </el-button>
            <el-button type="primary" @click="finish(cfg.finish_action?.primary_route)">
              {{ cfg.footer.finish || '知道了' }}
            </el-button>
          </template>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  closeGuideModal,
  flushPendingGuide,
  guideModalState,
  markGuideSeen,
} from '@/composables/useGuideModal'

const router = useRouter()

const visible = computed({
  get: () => guideModalState.open,
  set: (v: boolean) => {
    if (!v) closeGuideModal(true)
    else guideModalState.open = v
  },
})

const cfg = computed(() => guideModalState.config)
const step = computed({
  get: () => guideModalState.step,
  set: (v: number) => {
    guideModalState.step = v
  },
})
const current = computed(() => cfg.value?.steps[step.value])
const isLast = computed(() => {
  if (!cfg.value) return false
  return step.value >= cfg.value.steps.length - 1
})

function skip() {
  visible.value = false
}

function finish(route?: string) {
  const config = cfg.value
  if (config) markGuideSeen(config)
  visible.value = false
  if (route) router.push(route)
}

function onClosed() {
  closeGuideModal(false)
  flushPendingGuide()
}
</script>

<style scoped>
.guide-header {
  text-align: left;
  padding-right: 24px;
}
.guide-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold, #d4a574);
  font-size: 0.75rem;
  margin-bottom: 8px;
}
.guide-title {
  margin: 0 0 6px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #f5f0e8;
}
.guide-subtitle {
  margin: 0;
  font-size: 0.88rem;
  color: var(--wc-text-muted, #9a94a8);
  line-height: 1.5;
}
.guide-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.step-track {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.step-dot {
  flex: 1;
  min-width: 52px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--wc-text-muted);
  padding: 6px 4px;
  cursor: pointer;
}
.step-dot.active {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.12);
  color: #f5f0e8;
}
.step-dot.done {
  opacity: 0.75;
}
.dot-num {
  display: block;
  font-size: 0.65rem;
}
.dot-label {
  display: block;
  font-size: 0.95rem;
  line-height: 1.2;
}
.step-card {
  display: flex;
  gap: 14px;
  padding: 16px;
  align-items: flex-start;
}
.step-icon {
  font-size: 2rem;
  line-height: 1;
  flex-shrink: 0;
}
.step-text h3 {
  margin: 0 0 8px;
  font-size: 1.05rem;
  color: #f5f0e8;
}
.step-desc {
  margin: 0 0 10px;
  color: var(--wc-text-muted);
  font-size: 0.9rem;
  line-height: 1.55;
}
.step-highlight {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid rgba(212, 165, 116, 0.25);
  color: var(--wc-accent-gold);
  font-size: 0.85rem;
  line-height: 1.5;
}
.step-bullets {
  margin: 0;
  padding-left: 1.1rem;
  color: #d0d7de;
  font-size: 0.88rem;
  line-height: 1.65;
}
.progress-bar {
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #d4a574, #e8c9a0);
  transition: width 0.25s ease;
}
.progress-hint {
  margin: 0;
  text-align: center;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}
.guide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>

<style>
.guide-modal-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
