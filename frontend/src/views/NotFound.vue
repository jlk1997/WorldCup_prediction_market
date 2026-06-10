<template>
  <div class="not-found page-shell">
    <div class="panel glass-panel">
      <h1>404</h1>
      <p>页面不存在或已被移除</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.panel {
  text-align: center;
  padding: 40px 48px;
}
.panel h1 {
  margin: 0 0 8px;
  font-size: 3rem;
  color: var(--wc-accent-gold);
}
.panel p {
  margin: 0 0 24px;
  color: var(--wc-text-muted);
}
</style>
