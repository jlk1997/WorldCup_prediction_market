<template>
  <div class="legal-page page-shell">
    <div class="content glass-panel">
      <h1>隐私政策</h1>
      <p>我们收集邮箱用于登录验证，以及您在平台内的竞猜与消费记录。</p>
      <h2>AI 数据处理</h2>
      <p>
        使用 AI 分析时，我们会处理您选择的对阵、赛事状态及公开新闻摘要；分析结果存储于平台用于缓存展示。
        第三方大模型服务商为 MiniMax。详见<router-link to="/legal/ai">AI 使用说明</router-link>。
      </p>
      <p>我们不会向第三方出售您的个人信息。支付信息由支付宝处理，我们不存储银行卡号。</p>
      <p>如需注销账号或导出数据，请联系客服。</p>
      <el-button plain @click="$router.back()">返回</el-button>
    </div>
  </div>
</template>

<style scoped>
.legal-page {
  padding: 24px;
  max-width: 720px;
  margin: 0 auto;
}
.content {
  padding: 28px;
  line-height: 1.7;
}
.content h1 {
  margin-top: 0;
}
</style>
