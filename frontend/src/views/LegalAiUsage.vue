<template>
  <div class="legal-page page-shell">
    <div class="content glass-panel">
      <h1>AI 分析使用说明</h1>
      <p>本平台 AI 多 Agent 分析功能由第三方大模型（MiniMax）提供算力支持，输出内容仅供球迷娱乐参考。</p>

      <h2>计费规则</h2>
      <ul>
        <li>未登录用户仅可浏览历史缓存摘要，不会触发 AI 分析，也不扣币。</li>
        <li>登录用户每日享有免费 AI 分析次数；超出后按模式扣球迷币（赛前 / 赛中价格不同）。</li>
        <li>若结果来自缓存（相同对阵近期已分析过），<strong>不扣球迷币</strong>。</li>
        <li>强制刷新会忽略缓存并重新调用 AI，可能消耗免费额度或额外扣币。</li>
        <li>持有有效赛季通行证的用户享有额外每日免费次数与每日领币权益。</li>
      </ul>

      <h2>免责声明</h2>
      <p>
        AI 输出不构成任何投注、购彩或投资建议。平台不对预测准确性、时效性作任何保证。
        请勿将 AI 结论作为唯一决策依据。
      </p>

      <h2>数据处理</h2>
      <p>
        分析时会使用您选择的对阵、赛事状态及公开新闻摘要作为输入；分析结果会存储于平台数据库用于缓存与展示。
        详见<router-link to="/legal/privacy">隐私政策</router-link>。
      </p>

      <el-button plain @click="$router.back()">返回</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({
  title: 'AI 使用说明 — 最后一舞',
  description: 'AI 分析功能的数据处理方式、计费规则与第三方模型说明。',
  path: '/legal/ai',
})
</script>

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
.content ul {
  padding-left: 1.2rem;
}
.content a {
  color: var(--wc-accent-gold);
}
</style>
