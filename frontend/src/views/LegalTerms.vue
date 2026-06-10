<template>
  <div class="legal-page page-shell">
    <div class="content glass-panel">
      <h1>用户服务协议</h1>
      <p>欢迎使用「最后一舞：世界杯2026」。本平台提供赛事数据、娱乐竞猜与球迷社区功能。</p>
      <h2>虚拟球迷币规则</h2>
      <p>球迷币可通过签到、问答、竞猜奖励与充值获得，用于 AI 分析、竞猜质押、助威等站内消费。</p>
      <p>球迷币、赛季积分、虚拟勋章均为平台内虚拟物品，<strong>不可提现、不可兑换现金、不可转赠</strong>。当前版本球迷币不设过期。</p>
      <h2>竞猜规则</h2>
      <p>竞猜仅供娱乐参考，不构成任何投资建议。请理性参与，未成年人请勿付费。</p>
      <h2>免责声明</h2>
      <p>AI 分析结果仅供参考，平台不对预测准确性作任何保证。</p>
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
.content h2 {
  margin-top: 24px;
  font-size: 1rem;
}
</style>
