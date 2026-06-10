<template>
  <div class="entitlement-preview" :class="{ compact }">
    <div class="preview-left">
      <div class="avatar-wrap" :class="avatarFrameClass(avatarFrame)">
        <span class="avatar-letter">{{ initial }}</span>
      </div>
      <div v-if="themeKey" class="theme-strip" :class="`theme-${themeKey}`">
        <span /><span /><span />
      </div>
    </div>
    <div class="preview-right">
      <ul v-if="grants.length" class="grant-list">
        <li v-for="(item, idx) in grants" :key="idx">{{ item }}</li>
      </ul>
      <p v-if="avatarFrame || themeKey" class="equipped">
        <span v-if="avatarFrame">{{ avatarFrameLabel(avatarFrame) }}</span>
        <span v-if="avatarFrame && themeKey"> · </span>
        <span v-if="themeKey">{{ themeKeyLabel(themeKey) }}</span>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  avatarFrameClass,
  avatarFrameLabel,
  themeKeyLabel,
} from '../utils/entitlements'

const props = withDefaults(
  defineProps<{
    avatarFrame?: string | null
    themeKey?: string | null
    grants?: string[]
    nickname?: string
    compact?: boolean
  }>(),
  {
    avatarFrame: null,
    themeKey: null,
    grants: () => [],
    nickname: '球',
    compact: false,
  },
)

const initial = computed(() => (props.nickname || '球').slice(0, 1))
</script>

<style scoped>
.entitlement-preview {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  width: 100%;
}

.entitlement-preview.compact {
  gap: 10px;
}

.preview-left {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.avatar-wrap {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(212, 165, 116, 0.15);
  border: 2px solid rgba(212, 165, 116, 0.35);
}

.avatar-wrap.frame-gold_wc {
  border: 3px solid #e8c88a;
  box-shadow: 0 0 0 2px rgba(232, 200, 138, 0.35), 0 0 16px rgba(212, 165, 116, 0.45);
}

.avatar-wrap.frame-silver_wc {
  border: 3px solid #c0c0c0;
  box-shadow: 0 0 0 2px rgba(192, 192, 192, 0.3), 0 0 12px rgba(200, 200, 200, 0.25);
}

.avatar-wrap.frame-referral_squad {
  border: 3px solid #c9788a;
  box-shadow: 0 0 12px rgba(201, 120, 138, 0.35);
}

.avatar-letter {
  font-size: 1.35rem;
  font-weight: 800;
  color: #f5f0e8;
}

.theme-strip {
  display: flex;
  gap: 4px;
  width: 56px;
}

.theme-strip span {
  flex: 1;
  height: 6px;
  border-radius: 3px;
}

.theme-strip.theme-team_spirit span:nth-child(1) {
  background: #d4a574;
}
.theme-strip.theme-team_spirit span:nth-child(2) {
  background: #c9788a;
}
.theme-strip.theme-team_spirit span:nth-child(3) {
  background: #2a3050;
}

.preview-right {
  flex: 1;
  min-width: 0;
}

.grant-list {
  margin: 0 0 6px;
  padding-left: 1.1rem;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.55;
}

.equipped {
  margin: 0;
  font-size: 0.78rem;
  color: var(--wc-accent-gold);
  font-weight: 600;
}

.compact .avatar-wrap {
  width: 48px;
  height: 48px;
}

.compact .grant-list {
  font-size: 0.78rem;
}
</style>
