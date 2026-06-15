<template>
  <Teleport to="body">
    <button
      v-if="visible"
      type="button"
      class="qq-group-fab touch-target"
      :class="{ 'has-reward': showRewardBadge }"
      :aria-label="config.fab_label"
      @click="openOfficialQqGroupModal"
    >
      <span class="fab-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22">
          <path
            fill="currentColor"
            d="M12 2C6.48 2 2 6.15 2 11c0 2.76 1.39 5.22 3.57 6.88L4 22l4.35-1.62C9.47 20.78 10.7 21 12 21c5.52 0 10-4.15 10-9s-4.48-9-10-9zm0 16c-1.1 0-2.16-.22-3.13-.62l-.22-.1-2.2.82.82-2.14-.14-.22A6.96 6.96 0 0 1 5 11c0-3.87 3.58-7 7-7s7 3.13 7 7-3.58 7-7 7z"
          />
        </svg>
      </span>
      <span class="fab-text">
        <strong>{{ config.fab_label }}</strong>
        <small v-if="config.fab_hint">{{ config.fab_hint }}</small>
      </span>
      <span v-if="showRewardBadge" class="fab-badge">+{{ config.reward_coins }}币</span>
    </button>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  ensureOfficialQqGroupConfig,
  officialQqGroupConfig,
  officialQqGroupState,
  openOfficialQqGroupModal,
} from '@/composables/useOfficialQqGroup'
import { isLoggedIn } from '@/stores/authStore'
import { isAuthFlowPath } from '@/composables/useGuideVisibility'

const route = useRoute()
const config = officialQqGroupConfig

const visible = computed(() => {
  if (!config.enabled) return false
  if (isAuthFlowPath(route.path)) return false
  return true
})

const showRewardBadge = computed(
  () => isLoggedIn.value && !officialQqGroupState.claimed && config.reward_coins > 0,
)

onMounted(() => {
  void ensureOfficialQqGroupConfig()
})
</script>

<style scoped>
.qq-group-fab {
  position: fixed;
  left: 12px;
  bottom: calc(var(--wc-bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px) + 14px);
  z-index: 190;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 10px 10px;
  border: 1px solid rgba(56, 189, 248, 0.45);
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.92), rgba(88, 28, 135, 0.88));
  color: #e0f2fe;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
  cursor: pointer;
  pointer-events: auto;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

@media (min-width: 769px) {
  .qq-group-fab {
    left: auto;
    right: 18px;
    bottom: 24px;
  }
}

.qq-group-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(56, 189, 248, 0.25);
}

.qq-group-fab.has-reward {
  animation: fab-pulse 2.4s ease-in-out infinite;
}

@keyframes fab-pulse {
  0%,
  100% {
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
  }
  50% {
    box-shadow: 0 8px 28px rgba(56, 189, 248, 0.45);
  }
}

.fab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}

.fab-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.15;
  text-align: left;
}

.fab-text strong {
  font-size: 0.82rem;
  font-weight: 700;
}

.fab-text small {
  font-size: 0.65rem;
  opacity: 0.85;
}

.fab-badge {
  position: absolute;
  top: -6px;
  right: -4px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #f59e0b;
  color: #1a1224;
  font-size: 0.62rem;
  font-weight: 800;
  white-space: nowrap;
}
</style>
