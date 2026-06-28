<template>
  <div class="login-page">
    <div class="login-card glass-panel">
      <h1>登录 · 最后一舞</h1>
      <p class="hint">邮箱验证码登录，新用户自动注册并赠送球迷币</p>

      <el-alert
        v-if="refPreview?.valid"
        type="success"
        :closable="false"
        show-icon
        class="ref-banner"
      >
        <template #title>
          {{ refPreview.inviter_nickname }} 邀请你加入
        </template>
        新用户注册可得 {{ refPreview.total_new_user_coins }} 球迷币（含邀请额外 +{{ refPreview.register_invitee_bonus }}）
      </el-alert>
      <el-alert
        v-else-if="refInvalid"
        type="info"
        :closable="true"
        show-icon
        class="ref-banner"
        title="邀请码无效或已失效，仍可正常注册获得新手礼包"
      />

      <div class="manual-ref">
        <button type="button" class="manual-ref-toggle" @click="showManualRef = !showManualRef">
          {{ showManualRef ? '收起邀请码' : '有邀请码？点此填写' }}
        </button>
        <div v-if="showManualRef" class="manual-ref-form">
          <el-input
            v-model="manualCode"
            maxlength="12"
            placeholder="输入 6–8 位邀请码"
            @blur="previewManualCode"
            @keyup.enter="previewManualCode"
          />
          <el-button plain size="small" :loading="previewLoading" @click="previewManualCode">验证</el-button>
        </div>
      </div>

      <el-alert
        v-if="rateLimitAlert"
        type="warning"
        :closable="false"
        show-icon
        class="rate-limit-alert"
        :title="rateLimitAlert"
      >
        <template v-if="sendCooldownSec > 0" #default>
          请等待 <strong>{{ sendCooldownSec }}</strong> 秒后再发送验证码
        </template>
      </el-alert>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="邮箱">
          <el-input v-model="email" type="email" placeholder="your@email.com" :disabled="step === 'code'" />
        </el-form-item>

        <el-form-item v-if="step === 'code'" label="验证码">
          <el-input v-model="code" maxlength="6" placeholder="6 位数字" />
        </el-form-item>

        <el-checkbox v-model="ageAgreed" class="age-check" :class="{ 'needs-attention': ageHintVisible && !ageAgreed }">
          我已满 18 周岁，并已阅读同意
          <router-link to="/legal/terms">用户协议</router-link>
          与
          <router-link to="/legal/privacy">隐私政策</router-link>
        </el-checkbox>
        <p v-if="ageHintVisible && !ageAgreed" class="age-hint">请先勾选协议，才能发送验证码或登录</p>

        <div class="actions">
          <el-button
            v-if="step === 'email'"
            type="primary"
            :loading="loading"
            :disabled="sendCooldownSec > 0"
            @click="onSendCode"
          >
            {{ sendCooldownSec > 0 ? `${sendCooldownSec}s 后可重发` : '发送验证码' }}
          </el-button>
          <template v-else>
            <el-button plain @click="step = 'email'">换邮箱</el-button>
            <el-button type="primary" :loading="loading" :disabled="verifying" @click="onVerify">登录</el-button>
          </template>
        </div>
      </el-form>

      <p class="disclaimer">本平台竞猜仅供娱乐，虚拟物品不可提现</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authState, isLoggedIn, sendCode, verifyCode } from '../stores/authStore'
import { fetchProfileStatus } from '../stores/profileStore'
import { isRateLimitError } from '../api/client'
import { showRateLimitError, showApiError } from '../utils/errorHandler'

import { previewReferralCode, type ReferralPreview } from '../api/referral'
import { usePageMeta } from '../composables/usePageMeta'
import { trackEvent } from '../utils/analytics'

usePageMeta({
  title: '登录 / 注册 — 最后一舞 · 世界杯2026',
  description: '邮箱验证码登录，新用户自动注册并赠送球迷币。邀请链接注册可获额外奖励。',
  path: '/login',
})

const router = useRouter()
const route = useRoute()

const email = ref('')
const code = ref('')
const step = ref<'email' | 'code'>('email')
const loading = ref(false)
const verifying = ref(false)
const ageAgreed = ref(false)
const ageHintVisible = ref(false)
const refPreview = ref<ReferralPreview | null>(null)
const refInvalid = ref(false)
const showManualRef = ref(false)
const manualCode = ref('')
const previewLoading = ref(false)
const rateLimitAlert = ref('')
const sendCooldownSec = ref(0)
let sendCooldownTimer: ReturnType<typeof setInterval> | null = null

function clearSendCooldown() {
  if (sendCooldownTimer) {
    clearInterval(sendCooldownTimer)
    sendCooldownTimer = null
  }
  sendCooldownSec.value = 0
}

function startSendCooldown(retryAfterMs: number, message: string) {
  clearSendCooldown()
  rateLimitAlert.value = message
  sendCooldownSec.value = Math.max(1, Math.ceil(retryAfterMs / 1000))
  sendCooldownTimer = setInterval(() => {
    sendCooldownSec.value -= 1
    if (sendCooldownSec.value <= 0) {
      clearSendCooldown()
      rateLimitAlert.value = ''
    }
  }, 1000)
}

onUnmounted(() => {
  clearSendCooldown()
})

const REF_STORAGE_KEY = 'wc2026_ref'

async function redirectAfterAuth(referralBound: boolean) {
  let profileDone = authState.user?.profile_completed ?? false
  try {
    const status = await fetchProfileStatus(true)
    if (status) profileDone = status.profile_completed
  } catch {
    /* optional */
  }
  if (!profileDone) {
    const fromReferral = referralBound ? '?from=referral' : ''
    await router.replace(`/onboarding${fromReferral}`)
    return
  }
  const redirect = (route.query.redirect as string) || '/predict'
  await router.replace(redirect)
}

onMounted(async () => {
  if (isLoggedIn.value) {
    await redirectAfterAuth(false)
    return
  }

  const refCode = route.query.ref ?? route.query.invite
  if (typeof refCode === 'string' && refCode.trim()) {
    const normalized = refCode.trim().toUpperCase()
    manualCode.value = normalized
    sessionStorage.setItem(REF_STORAGE_KEY, normalized)
    await applyRefPreview(normalized)
  }
})

async function applyRefPreview(normalized: string) {
  try {
    const preview = await previewReferralCode(normalized)
    if (preview.valid) {
      refPreview.value = preview
      refInvalid.value = false
    } else {
      refPreview.value = null
      refInvalid.value = true
    }
  } catch {
    refInvalid.value = false
  }
}

async function previewManualCode() {
  const normalized = manualCode.value.trim().toUpperCase()
  if (!normalized || normalized.length < 4) return
  manualCode.value = normalized
  previewLoading.value = true
  try {
    sessionStorage.setItem(REF_STORAGE_KEY, normalized)
    await applyRefPreview(normalized)
  } finally {
    previewLoading.value = false
  }
}

function consumeInviteCode(): string | undefined {
  const manual = manualCode.value.trim().toUpperCase()
  if (manual.length >= 4) return manual
  const stored = sessionStorage.getItem(REF_STORAGE_KEY)
  if (stored) return stored
  const q = route.query.ref ?? route.query.invite
  if (typeof q === 'string' && q.trim()) return q.trim().toUpperCase()
  return undefined
}

function normalizeEmail(raw: string) {
  return raw.trim().toLowerCase()
}

async function onSendCode() {
  if (!ageAgreed.value) {
    ageHintVisible.value = true
    ElMessage.warning('请先勾选已满 18 周岁并同意协议')
    return
  }
  const addr = normalizeEmail(email.value)
  if (!addr.includes('@')) {
    ElMessage.warning('请输入有效邮箱')
    return
  }
  email.value = addr
  loading.value = true
  rateLimitAlert.value = ''
  try {
    await sendCode(addr, ageAgreed.value)
    step.value = 'code'
    code.value = ''
    clearSendCooldown()
    ElMessage.success('验证码已发送到邮箱，请查收（含垃圾箱）')
  } catch (e) {
    if (isRateLimitError(e)) {
      const msg = showRateLimitError(
        e,
        '验证码发送过于频繁，请稍后再试',
      )
      startSendCooldown(e.retryAfterMs, msg)
    } else {
      showApiError(e, '验证码发送失败，请稍后再试')
    }
  } finally {
    loading.value = false
  }
}

async function onVerify() {
  if (!ageAgreed.value) {
    ageHintVisible.value = true
    ElMessage.warning('请先勾选已满 18 周岁并同意协议')
    return
  }
  if (verifying.value) return
  const addr = normalizeEmail(email.value)
  if (code.value.length < 4) {
    ElMessage.warning('请输入验证码')
    return
  }
  verifying.value = true
  loading.value = true
  try {
    const inviteUsed = consumeInviteCode()
    const data = await verifyCode(addr, code.value.trim(), ageAgreed.value, inviteUsed)
    sessionStorage.removeItem(REF_STORAGE_KEY)
    if (data.is_new) {
      trackEvent('register_success', { has_invite: String(!!inviteUsed) })
      if (data.referral?.bound) {
        trackEvent('invite_bound', { inviter: data.referral.inviter_nickname || '' })
      }
      const attempted = !!inviteUsed || !!data.referral?.invite_code_attempted
      if (data.referral?.bound && data.referral.inviter_nickname) {
        ElMessage.success(
          `注册成功！${data.referral.inviter_nickname} 邀请你加入，已到账新手礼包（含邀请奖励）`,
        )
      } else if (attempted && !data.referral?.bound) {
        ElMessage.warning(
          data.referral?.message || '邀请码未生效（可能无效、已达上限或你已绑定过），你仍已获得新手球迷币',
        )
      } else if (data.referral?.message) {
        ElMessage.success(data.referral.message)
      } else {
        ElMessage.success('注册成功，已赠送新手球迷币')
      }
    } else {
      ElMessage.success('登录成功')
    }
    await redirectAfterAuth(!!data.referral?.bound)
  } catch (e) {
    if (isRateLimitError(e)) {
      showRateLimitError(e, '登录尝试过于频繁，请稍后再试')
    } else {
      showApiError(e)
    }
  } finally {
    loading.value = false
    verifying.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 28px;
  min-height: calc(var(--app-height, 100dvh) - var(--wc-header-height));
  padding: 24px;
  background: transparent;
}

.login-legends {
  flex: 0 1 360px;
  max-width: 380px;
}

.login-legends-mobile {
  width: 100%;
  max-width: 420px;
  margin-bottom: -8px;
}
.login-card {
  width: 100%;
  max-width: 420px;
  padding: 28px;
}
.login-card h1 {
  margin: 0 0 8px;
  font-size: 1.5rem;
  color: var(--wc-text-primary);
}
.hint {
  color: var(--wc-text-muted);
  margin-bottom: 20px;
  font-size: 0.9rem;
}
.rate-limit-alert {
  margin-bottom: 16px;
}
.rate-limit-alert strong {
  color: var(--wc-accent-gold);
}
.ref-banner {
  margin-bottom: 16px;
}
.manual-ref {
  margin-bottom: 16px;
}
.manual-ref-toggle {
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  cursor: pointer;
  padding: 0;
}
.manual-ref-toggle:hover {
  text-decoration: underline;
}
.manual-ref-form {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.manual-ref-form .el-input {
  flex: 1;
}
.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.legal, .disclaimer {
  margin-top: 20px;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}
.age-check {
  margin: 12px 0 4px;
  line-height: 1.5;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
}
.age-check a {
  color: var(--wc-accent-gold);
}
.age-check.needs-attention {
  outline: 1px solid rgba(201, 120, 138, 0.45);
  border-radius: 6px;
  padding: 4px 6px;
}
.age-hint {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--wc-accent-rose);
}

@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
    padding: 16px;
    gap: 12px;
    min-height: calc(var(--app-height, 100dvh) - var(--wc-mobile-header-height));
  }

  .login-card {
    padding: 20px 16px;
    margin: 0;
    max-width: 100%;
  }
  .actions {
    flex-direction: column;
  }
  .actions .el-button {
    width: 100%;
    min-height: 44px;
  }
}
</style>
