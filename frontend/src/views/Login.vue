<template>
  <div class="login-page">
    <LegendsShowcase variant="hero" title="与传奇同框" class="login-legends hide-mobile" />
    <LegendsShowcase variant="strip" :show-labels="false" class="login-legends-mobile hide-desktop" />

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
          <el-button v-if="step === 'email'" type="primary" :loading="loading" @click="onSendCode">
            发送验证码
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authState, isLoggedIn, sendCode, verifyCode } from '../stores/authStore'
import { fetchProfileStatus } from '../stores/profileStore'
import { showApiError } from '../utils/errorHandler'

import { previewReferralCode, type ReferralPreview } from '../api/referral'
import LegendsShowcase from '../components/LegendsShowcase.vue'

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

const REF_STORAGE_KEY = 'wc2026_ref'

async function redirectAfterAuth(referralBound: boolean) {
  let profileDone = authState.user?.profile_completed ?? false
  try {
    const status = await fetchProfileStatus(true)
    profileDone = status.profile_completed
  } catch {
    /* optional */
  }
  if (!profileDone) {
    const fromReferral = referralBound ? '?from=referral' : ''
    await router.replace(`/onboarding${fromReferral}`)
    return
  }
  const redirect = (route.query.redirect as string) || '/'
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
    sessionStorage.setItem(REF_STORAGE_KEY, normalized)
    try {
      const preview = await previewReferralCode(normalized)
      if (preview.valid) {
        refPreview.value = preview
        refInvalid.value = false
      } else {
        refInvalid.value = true
      }
    } catch {
      refInvalid.value = false
    }
  }
})

function consumeInviteCode(): string | undefined {
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
  try {
    await sendCode(addr, ageAgreed.value)
    step.value = 'code'
    code.value = ''
    ElMessage.success('验证码已发送到邮箱，请查收（含垃圾箱）')
  } catch (e) {
    showApiError(e)
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
    const data = await verifyCode(addr, code.value.trim(), ageAgreed.value, consumeInviteCode())
    sessionStorage.removeItem(REF_STORAGE_KEY)
    if (data.is_new) {
      if (data.referral?.bound && data.referral.inviter_nickname) {
        ElMessage.success(
          `注册成功！${data.referral.inviter_nickname} 邀请你加入，已到账新手礼包（含邀请奖励）`
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
    showApiError(e)
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
  min-height: calc(100vh - var(--wc-header-height));
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
.ref-banner {
  margin-bottom: 16px;
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
    min-height: calc(100dvh - var(--wc-mobile-header-height));
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
