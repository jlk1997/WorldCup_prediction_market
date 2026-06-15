<template>
  <div class="wc-guide page-shell">
    <article class="hero glass-panel">
      <p class="eyebrow">2026 FIFA World Cup · 美加墨</p>
      <h1>最后一舞：世界杯2026 球迷互动指南</h1>
      <p class="lead">
        免费注册即可参与娱乐竞猜、AI 赛事分析、球迷擂台与排行榜。虚拟球迷币不可提现，仅供站内娱乐。
      </p>
      <div class="cta-row">
        <el-button type="primary" size="large" @click="$router.push('/login')">免费注册 / 登录</el-button>
        <el-button plain size="large" @click="$router.push('/predict')">去竞猜大厅</el-button>
      </div>
    </article>

    <section class="section glass-panel">
      <h2>2026 世界杯一览</h2>
      <ul class="fact-list">
        <li><strong>时间</strong>：2026 年 6–7 月（具体赛程以官方公布为准）</li>
        <li><strong>主办</strong>：美国、加拿大、墨西哥联合举办，48 支球队</li>
        <li><strong>本站</strong>：赛程大屏、实时比分、球队库、资讯聚合与球迷互动</li>
      </ul>
      <div class="link-row">
        <router-link to="/live">赛事中心</router-link>
        <router-link to="/teams">48 支球队库</router-link>
        <router-link to="/news">世界杯资讯</router-link>
        <router-link to="/leaderboard">球迷排行榜</router-link>
      </div>
    </section>

    <section class="section glass-panel">
      <h2>怎么玩</h2>
      <div class="steps">
        <div v-for="s in steps" :key="s.title" class="step-card glass-inner">
          <strong>{{ s.title }}</strong>
          <p>{{ s.desc }}</p>
        </div>
      </div>
    </section>

    <section id="faq" class="section glass-panel">
      <h2>常见问题</h2>
      <div v-for="item in faqItems" :key="item.q" class="faq-item">
        <h3>{{ item.q }}</h3>
        <p>{{ item.a }}</p>
      </div>
    </section>

    <section class="section glass-panel cta-bottom">
      <h2>现在加入</h2>
      <p>邮箱验证码注册，新用户赠送球迷币。邀请好友双方还可得奖励。</p>
      <el-button type="primary" @click="$router.push('/login')">立即开始</el-button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { usePageMeta } from '../composables/usePageMeta'
import { injectJsonLd } from '../utils/jsonLd'

const steps = [
  { title: '1. 注册并选主队', desc: '完善球迷档案，获得个性化赛程与问答。' },
  { title: '2. 每日签到 / 问答', desc: '领球迷币，完成今日任务。' },
  { title: '3. 竞猜 / 擂台 / AI', desc: '猜比分冲榜，或用 AI 多 Agent 看战术。' },
  { title: '4. 邀友一起玩', desc: '分享邀请链接，好友注册后双方得币。' },
]

const faqItems = [
  {
    q: '「最后一舞」是什么？',
    a: '面向 2026 世界杯的球迷互动网站，提供赛程、竞猜娱乐、排行榜、AI 分析与召友玩法，非官方 FIFA 产品。',
  },
  {
    q: '要花钱吗？',
    a: '注册与大量玩法免费。球迷币可通过签到、问答、竞猜获得，也可充值购买虚拟道具；不可提现。',
  },
  {
    q: '竞猜是赌博吗？',
    a: '本站竞猜仅供娱乐，使用虚拟球迷币与积分，不构成投资建议。请理性参与，须年满 18 周岁。',
  },
  {
    q: '如何邀请好友？',
    a: '登录后在球迷中心或竞猜页点击「分享给好友」，复制链接发给微信好友即可。好友完成档案后双方得球迷币。',
  },
  {
    q: '在哪里看赛程和比分？',
    a: '首页赛事大屏与「赛事中心」提供赛程与 Live 比分；球队详情见球队库。',
  },
  {
    q: '球迷币和积分有什么区别？',
    a: '球迷币用于竞猜质押、AI 分析、助威等消费；累计积分与可用积分用于排行榜与兑换商城，均不可提现。',
  },
  {
    q: '免费竞猜有几次？',
    a: '登录用户每日有免费竞猜次数（以竞猜页显示为准）。免费猜中同样可获得积分奖励。',
  },
  {
    q: 'AI 分析怎么收费？',
    a: '登录用户每日有免费 AI 次数；超出后按模式扣球迷币。命中缓存的历史分析不重复扣币。详见 AI 使用说明。',
  },
  {
    q: '如何加入官方 QQ 群？',
    a: '点击页面右下角 QQ 群入口，加入后可领取一次性 50 球迷币奖励（每账号限领一次）。',
  },
  {
    q: '猜中了怎么分享？',
    a: '结算弹窗点击「分享战绩」复制带预览的链接；也可在球迷名片生成海报或分享公开名片页。',
  },
  {
    q: '2026 世界杯什么时候踢？',
    a: '2026 美加墨世界杯于 2026 年 6–7 月举行。本站赛程中心可查看全部 104 场对阵与时间。',
  },
  {
    q: '支持哪些球队？',
    a: '48 支参赛队均已收录，可在球队库查看各队资料、阵容与赛程。',
  },
  {
    q: '排行榜怎么算？',
    a: '累计积分来自猜中等行为；军团榜看主队贡献；召友榜统计有效邀请。赛后上榜用户可获平台回馈（以公告为准）。',
  },
  {
    q: '虚拟奖励能提现吗？',
    a: '不能。球迷币、积分、虚拟装扮均为站内娱乐道具，不可兑换现金或转赠。',
  },
  {
    q: '忘记密码怎么办？',
    a: '本站使用邮箱验证码登录，无需密码。若无法收到验证码，请检查垃圾箱或联系客服。',
  },
]

usePageMeta({
  title: '2026 世界杯球迷指南 — 竞猜、赛程、AI 分析 | 最后一舞',
  description:
    '2026 美加墨世界杯球迷互动指南：免费注册参与娱乐竞猜、实时赛程、球队库、AI 分析与排行榜。虚拟道具不可提现，18+ 理性娱乐。',
  path: '/worldcup2026',
})

onMounted(() => {
  injectJsonLd({
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'FAQPage',
        mainEntity: faqItems.map((item) => ({
          '@type': 'Question',
          name: item.q,
          acceptedAnswer: { '@type': 'Answer', text: item.a },
        })),
      },
      {
        '@type': 'WebSite',
        name: '最后一舞',
        url: 'https://loveaibaby.cn/',
        description:
          '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。',
      },
      {
        '@type': 'Organization',
        name: '最后一舞',
        url: 'https://loveaibaby.cn/',
        logo: 'https://loveaibaby.cn/share-og.png',
      },
    ],
  })
})
</script>

<style scoped>
.wc-guide {
  max-width: 800px;
  margin: 0 auto;
  padding: 16px 16px 48px;
}

.hero {
  padding: 28px 24px;
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 0.8rem;
  color: var(--wc-accent-gold);
  letter-spacing: 0.05em;
}

.hero h1 {
  margin: 0 0 12px;
  font-size: 1.65rem;
  font-family: var(--wc-font-serif);
  line-height: 1.3;
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.lead {
  margin: 0 0 20px;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.78);
}

.cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.section {
  padding: 22px 24px;
  margin-bottom: 16px;
}

.section h2 {
  margin: 0 0 14px;
  font-size: 1.1rem;
  color: #f0d9b5;
}

.fact-list {
  margin: 0 0 16px;
  padding-left: 1.2rem;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.82);
}

.link-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
}

.link-row a {
  color: var(--wc-accent-gold);
  font-size: 0.9rem;
  text-decoration: none;
}

.link-row a:hover {
  text-decoration: underline;
}

.steps {
  display: grid;
  gap: 10px;
}

.step-card {
  padding: 14px 16px;
  border-radius: 10px;
}

.step-card strong {
  display: block;
  margin-bottom: 6px;
  color: #f5f0e8;
}

.step-card p {
  margin: 0;
  font-size: 0.88rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}

.faq-item {
  margin-bottom: 16px;
}

.faq-item h3 {
  margin: 0 0 6px;
  font-size: 0.95rem;
  color: #f5f0e8;
}

.faq-item p {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.75);
}

.cta-bottom {
  text-align: center;
}

.cta-bottom p {
  margin: 0 0 16px;
  color: var(--wc-text-muted);
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .cta-row .el-button {
    width: 100%;
    min-height: 44px;
  }
}
</style>
