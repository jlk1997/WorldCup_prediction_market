<template>
  <Transition name="sticky-slide">
    <div v-if="visible" class="pass-sticky">
      <div class="pass-sticky-inner glass-panel">
        <div class="sticky-text">
          <strong>手册 {{ claimableCount }} 项待领取</strong>
          <span>Lv.{{ level }} · 玩法升级即可领奖励</span>
        </div>
        <el-button type="primary" size="small" @click="$emit('open-pass')">去领取</el-button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  claimableCount?: number
  level?: number
  activeTab?: string
}>()

defineEmits<{ 'open-pass': [] }>()

const visible = computed(
  () => (props.claimableCount ?? 0) > 0 && props.activeTab !== 'pass',
)
</script>

<style scoped>
.pass-sticky {
  position: fixed;
  left: 0;
  right: 0;
  bottom: calc(var(--wc-bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px) + 8px);
  z-index: 40;
  padding: 0 12px;
  pointer-events: none;
}

.pass-sticky-inner {
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(61, 214, 140, 0.45);
  background: rgba(14, 16, 32, 0.92);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.sticky-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sticky-text strong {
  font-size: 0.85rem;
  color: #3dd68c;
}

.sticky-text span {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.sticky-slide-enter-active,
.sticky-slide-leave-active {
  transition: transform 0.28s ease, opacity 0.28s ease;
}

.sticky-slide-enter-from,
.sticky-slide-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
