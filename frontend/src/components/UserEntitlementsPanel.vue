<template>
  <div class="entitlements-panel">
    <h2 class="panel-title">我的权益</h2>

    <div class="entitlement-card glass-inner pass-card">
      <div class="card-head">
        <strong>赛季通行证</strong>
        <span class="status-pill" :class="passActive ? 'active' : 'expired'">
          {{ passActive ? '生效中' : passExpired ? '已过期' : '未开通' }}
        </span>
      </div>
      <template v-if="passActive">
        <p class="until">有效期至 {{ formatPassUntil(user?.season_pass_until) }}</p>
        <ul class="benefits">
          <li v-for="(line, idx) in seasonPassBenefitLines()" :key="idx">{{ line }}</li>
        </ul>
      </template>
      <p v-else-if="passExpired" class="hint">续费后可恢复积分加成与每日领币</p>
      <p v-else class="hint">购买赛季通行证解锁积分加成、每日领币与额外 AI 次数</p>
      <el-button v-if="!passActive" type="primary" plain size="small" @click="$router.push('/shop')">
        去商城开通
      </el-button>
    </div>

    <div v-if="hasCosmetic" class="entitlement-card glass-inner cosmetic-card">
      <div class="card-head">
        <strong>我的装扮</strong>
        <el-button link type="primary" size="small" @click="$router.push('/me/card')">查看球迷名片</el-button>
      </div>
      <EntitlementPreview
        :avatar-frame="user?.avatar_frame"
        :theme-key="user?.theme_key"
        :nickname="user?.nickname"
        :grants="cosmeticGrants"
        compact
      />
    </div>

    <div v-else class="entitlement-card glass-inner cosmetic-card muted">
      <div class="card-head">
        <strong>我的装扮</strong>
      </div>
      <p class="hint">购买主队装扮包可获得头像金框与全站主题色</p>
      <el-button type="primary" plain size="small" @click="$router.push('/shop')">去商城看看</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import EntitlementPreview from './EntitlementPreview.vue'
import {
  avatarFrameLabel,
  formatPassUntil,
  hasActiveSeasonPass,
  seasonPassBenefitLines,
  themeKeyLabel,
  type EntitlementUserLike,
} from '../utils/entitlements'

const props = defineProps<{
  user: EntitlementUserLike | null | undefined
}>()

const passActive = computed(() => hasActiveSeasonPass(props.user))
const passExpired = computed(
  () => !!props.user?.has_season_pass && !passActive.value,
)
const hasCosmetic = computed(
  () => !!(props.user?.avatar_frame || props.user?.theme_key),
)

const cosmeticGrants = computed(() => {
  const lines: string[] = []
  const frame = avatarFrameLabel(props.user?.avatar_frame)
  const theme = themeKeyLabel(props.user?.theme_key)
  if (frame) lines.push(`已装备 ${frame}`)
  if (theme) lines.push(`已启用 ${theme}`)
  return lines
})
</script>

<style scoped>
.entitlements-panel {
  margin-bottom: 16px;
}

.panel-title {
  margin: 0 0 12px;
  font-size: 1rem;
  font-weight: 700;
  color: #f0d9b5;
}

.entitlement-card {
  padding: 14px 16px;
  border-radius: 12px;
  margin-bottom: 12px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.card-head strong {
  color: #f5f0e8;
  font-size: 0.95rem;
}

.status-pill {
  font-size: 0.72rem;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 700;
}

.status-pill.active {
  background: rgba(103, 194, 58, 0.18);
  color: #8fd48a;
}

.status-pill.expired {
  background: rgba(255, 255, 255, 0.08);
  color: var(--wc-text-muted);
}

.until {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: var(--wc-accent-gold);
}

.benefits {
  margin: 0 0 10px;
  padding-left: 1.1rem;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.55;
}

.hint {
  margin: 0 0 10px;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}

.cosmetic-card.muted {
  opacity: 0.92;
}
</style>
