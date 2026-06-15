<template>
  <div class="news-page">
    <header class="page-header">
      <div class="head-row">
        <div>
          <h1>资讯中心</h1>
          <p v-if="mainTeamName && !filterTeam" class="personal-hint">
            已按主队 <strong>{{ mainTeamName }}</strong> 优先
            <span v-if="subTeamName"> · 副队 {{ subTeamName }}</span>
          </p>
        </div>
        <div class="head-actions">
          <el-input v-model="filterTeam" placeholder="按球队筛选" clearable class="team-filter" />
          <button type="button" class="refresh-btn" :disabled="loading" @click="refresh">
            {{ loading ? '刷新中…' : '刷新' }}
          </button>
        </div>
      </div>
    </header>

    <el-tabs v-model="activeLang" class="lang-tabs tabs-scroll" @tab-change="refresh">
      <el-tab-pane name="zh">
        <template #label>
          <span>中文资讯</span>
          <el-badge v-if="stats.zh" :value="stats.zh" class="tab-badge" type="warning" />
        </template>
      </el-tab-pane>
      <el-tab-pane name="en">
        <template #label>
          <span>国际资讯</span>
          <el-badge v-if="stats.en" :value="stats.en" class="tab-badge" />
        </template>
      </el-tab-pane>
      <el-tab-pane label="全部" name="all" />
    </el-tabs>

    <div class="article-list">
      <article
        v-for="a in articles"
        :key="a.id"
        class="article-card glass-panel"
        :class="{ 'my-team': a.for_my_team }"
      >
        <div class="card-main">
          <div class="card-top">
            <el-tag v-if="a.for_my_team" size="small" type="warning" effect="dark">我的主队</el-tag>
            <el-tag v-else-if="a.for_sub_team" size="small" type="info" effect="plain">我的副队</el-tag>
            <el-tag size="small" :type="a.lang === 'zh' ? 'warning' : 'info'" effect="plain">
              {{ a.lang === 'zh' ? '中文' : 'EN' }}
            </el-tag>
            <span class="source">{{ a.source }}</span>
          </div>

          <h2 class="title">
            <a v-if="a.url" :href="a.url" target="_blank" rel="noopener noreferrer">{{ a.title }}</a>
            <span v-else>{{ a.title }}</span>
          </h2>

          <p class="summary" :class="{ placeholder: !hasTextSummary(a) }">
            {{ summaryText(a) }}
          </p>

          <div class="card-foot">
            <span v-if="a.published_at" class="time">{{ formatDate(a.published_at) }}</span>
            <div v-if="a.team_tags?.length" class="tags">
              <span v-for="t in a.team_tags.slice(0, 4)" :key="t" class="team-tag">{{ t }}</span>
            </div>
            <a v-if="a.url" :href="a.url" target="_blank" rel="noopener noreferrer" class="read-link">
              阅读原文 →
            </a>
          </div>
        </div>

        <a
          v-if="thumbUrl(a) && !brokenThumbs.has(a.id)"
          :href="a.url || undefined"
          target="_blank"
          rel="noopener noreferrer"
          class="card-thumb"
        >
          <img :src="thumbUrl(a)!" :alt="a.title" loading="lazy" @error="onThumbError(a.id)" />
        </a>
      </article>

      <div v-if="loading && !articles.length" class="loading-hint">加载资讯中…</div>
      <el-empty v-else-if="!loading && !articles.length" :description="emptyText" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getNews, getNewsStats, type NewsArticle } from '@/api/news'
import { authState } from '@/stores/authStore'
import { profileState } from '@/stores/profileStore'
import { newsSummaryDisplay } from '@/utils/newsText'
import { usePageMeta } from '@/composables/usePageMeta'

usePageMeta({
  title: '世界杯资讯 — 最后一舞',
  description: '2026 世界杯相关新闻 RSS 聚合，支持中英文资讯与按球队筛选。',
  path: '/news',
})

const filterTeam = ref('')
const activeLang = ref<'zh' | 'en' | 'all'>('zh')
const articles = ref<NewsArticle[]>([])
const stats = ref({ en: 0, zh: 0, total: 0 })
const loading = ref(false)
const brokenThumbs = ref(new Set<number>())

const mainTeamName = computed(
  () =>
    profileState.recommendations?.fan_identity?.main_team?.name ??
    profileState.status?.main_team?.name ??
    null,
)
const subTeamName = computed(
  () =>
    profileState.recommendations?.fan_identity?.secondary_team?.name ??
    profileState.status?.secondary_team?.name ??
    null,
)

const emptyText = computed(() => {
  if (activeLang.value === 'zh') return '暂无中文资讯，请稍后刷新'
  if (activeLang.value === 'en') return '暂无国际资讯'
  return '暂无新闻'
})

function summaryText(a: NewsArticle) {
  const fromApi = a.summary?.trim()
  if (fromApi && !fromApi.includes('&lt;') && !fromApi.includes('data-hupu-node')) {
    return fromApi
  }
  return newsSummaryDisplay(a.summary, !!a.url)
}

function hasTextSummary(a: NewsArticle) {
  const t = summaryText(a)
  return t !== '本文为图文资讯，点击标题查看详情与配图' && t !== '暂无文字摘要'
}

function thumbUrl(a: NewsArticle) {
  return a.thumbnail_url || null
}

function onThumbError(id: number) {
  brokenThumbs.value = new Set([...brokenThumbs.value, id])
}

async function refresh() {
  loading.value = true
  brokenThumbs.value = new Set()
  try {
    const [list, st] = await Promise.all([
      getNews({
        lang: activeLang.value,
        team: filterTeam.value || undefined,
        limit: 40,
        personalize: !filterTeam.value && !!authState.accessToken,
      }),
      getNewsStats(),
    ])
    articles.value = list
    stats.value = st
  } finally {
    loading.value = false
  }
}

function formatDate(d: string) {
  return new Date(d).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(refresh)
watch(filterTeam, refresh)
</script>

<style scoped>
.news-page {
  max-width: 920px;
  margin: 0 auto;
  padding: 16px 20px 32px;
  min-height: min-content;
  background: transparent;
}

.page-header {
  margin-bottom: 14px;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.personal-hint {
  margin: 0;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
}

.personal-hint strong {
  color: var(--wc-accent-gold);
}

.head-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.team-filter {
  width: 180px;
}

.refresh-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.lang-tabs {
  margin-bottom: 14px;
}

.tab-badge {
  margin-left: 6px;
}

.article-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.article-card {
  display: flex;
  gap: 16px;
  padding: 16px 18px;
  align-items: stretch;
}

.article-card.my-team {
  border: 1px solid rgba(212, 165, 116, 0.35);
  box-shadow: 0 0 18px rgba(212, 165, 116, 0.1);
}

.card-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.source {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.45);
}

.title {
  margin: 0 0 10px;
  font-size: 1.05rem;
  line-height: 1.45;
  font-weight: 700;
}

.title a {
  color: #f0d9b5;
  text-decoration: none;
}

.title a:hover {
  color: var(--wc-accent-gold);
  text-decoration: underline;
}

.summary {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.78);
  flex: 1;
}

.summary.placeholder {
  color: rgba(255, 255, 255, 0.5);
  font-style: italic;
}

.card-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  font-size: 0.8rem;
}

.time {
  color: rgba(255, 255, 255, 0.45);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.team-tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  background: rgba(201, 120, 138, 0.15);
  color: #f0a0b0;
  border: 1px solid rgba(201, 120, 138, 0.25);
}

.read-link {
  margin-left: auto;
  color: var(--wc-accent-gold);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.82rem;
}

.read-link:hover {
  text-decoration: underline;
}

.card-thumb {
  flex-shrink: 0;
  width: 120px;
  height: 88px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.25);
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.loading-hint {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.55);
}

@media (max-width: 640px) {
  .news-page {
    padding: 12px;
  }
  .page-header h1 {
    font-size: 1.35rem;
  }
  .article-card {
    flex-direction: column-reverse;
  }

  .card-thumb {
    width: 100%;
    height: 160px;
  }

  .head-actions {
    width: 100%;
  }

  .team-filter {
    flex: 1;
  }
}
</style>
