<template>
  <div class="guest-login-banner glass-inner">
    <div class="guest-text">
      <strong>登录后免费猜球</strong>
      <span>每天 1 次免费竞猜 · 猜中拿积分冲榜 · 注册送 100 球迷币</span>
    </div>
    <el-button type="primary" size="small" @click="$router.push('/login')">立即登录</el-button>
  </div>
</template>

<style scoped>
.guest-login-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-top: 12px;
  border-radius: 12px;
  border: 1px solid rgba(88, 166, 255, 0.35);
  background: rgba(88, 166, 255, 0.08);
}

.guest-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.guest-text strong {
  font-size: 0.88rem;
  color: #f5f0e8;
}

.guest-text span {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
}
</style>
