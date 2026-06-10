<template>
  <div class="teams-page mobile-page">
    <header class="teams-head glass-panel">
      <h1>参赛球队</h1>
      <p class="teams-sub">48 支球队 · 点击卡片查看完整档案</p>
    </header>

    <div v-loading="loading" class="team-cards">
      <button
        v-for="row in tableData"
        :key="row.id"
        type="button"
        class="team-card glass-panel"
        @click="$router.push(`/teams/${encodeURIComponent(row.name)}`)"
      >
        <div class="team-card-top">
          <strong class="team-name">{{ row.name }}</strong>
          <span v-if="row.fifa_ranking" class="fifa">#{{ row.fifa_ranking }}</span>
        </div>
        <div class="team-card-meta">
          <span v-if="row.group_name" class="meta-chip">小组 {{ row.group_name }}</span>
          <span v-if="row.coach" class="meta-chip coach">{{ row.coach }}</span>
        </div>
      </button>

      <div v-if="!loading && !tableData.length" class="empty-block glass-panel">
        <p>暂无球队数据</p>
        <el-button type="primary" size="small" @click="fetchTeams">重新加载</el-button>
      </div>
    </div>

    <!-- 桌面端表格 -->
    <el-card v-if="!isMobile" class="desktop-table-card">
      <template #header>
        <span>球队列表</span>
      </template>
      <div class="table-scroll-wrap">
        <el-table :data="tableData" class="teams-table-compact" style="width: 100%" v-loading="loading">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="name" label="球队名称" width="180">
            <template #default="{ row }">
              <router-link :to="`/teams/${encodeURIComponent(row.name)}`" class="team-link">
                {{ row.name }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="country_code" label="国家代码" width="120" />
          <el-table-column prop="group_name" label="所在小组" width="120" />
          <el-table-column prop="fifa_ranking" label="FIFA排名" width="120" />
          <el-table-column prop="coach" label="主教练" />
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button size="small" type="primary" @click="$router.push(`/teams/${encodeURIComponent(scope.row.name)}`)">
                查看档案
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '../api/client'
import type { TeamBrief } from '../types/api'
import { useBreakpoint } from '../composables/useBreakpoint'

const { isMobile } = useBreakpoint()
const loading = ref(false)
const tableData = ref<TeamBrief[]>([])

async function fetchTeams() {
  loading.value = true
  try {
    const res = await apiClient.get<TeamBrief[]>('/api/teams')
    tableData.value = res.data
  } catch {
    ElMessage.error('获取球队数据失败，请检查后端或数据库连接')
  } finally {
    loading.value = false
  }
}

onMounted(fetchTeams)
</script>

<style scoped>
.teams-page {
  max-width: 1200px;
  margin: 0 auto;
  min-height: min-content;
}

.teams-head {
  padding: 16px 18px;
  margin-bottom: 14px;
  width: 100%;
}

.teams-head h1 {
  margin: 0 0 6px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #f5f0e8;
}

.teams-sub {
  margin: 0;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
}

.team-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-height: 120px;
}

.team-card {
  width: 100%;
  text-align: left;
  padding: 16px 18px;
  border: 1px solid rgba(212, 165, 116, 0.22);
  border-radius: var(--wc-radius-md);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.team-card:active {
  background: rgba(212, 165, 116, 0.12);
}

.team-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.team-name {
  font-size: 1.05rem;
  color: #f5f0e8;
  line-height: 1.3;
}

.fifa {
  font-size: 0.8rem;
  color: #1a1208;
  font-weight: 800;
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 8px;
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
}

.team-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-chip {
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
}

.meta-chip.coach {
  color: rgba(255, 255, 255, 0.82);
}

.empty-block {
  padding: 24px;
  text-align: center;
  color: var(--wc-text-muted);
}

.team-link {
  color: var(--wc-accent-gold-light);
  text-decoration: none;
  font-weight: 600;
}

.desktop-table-card {
  width: 100%;
}

@media (min-width: 769px) {
  .teams-page {
    padding: 16px 20px 32px;
  }

  .team-cards {
    display: none;
  }
}

@media (max-width: 768px) {
  .teams-head {
    padding: 14px 16px;
  }

  .desktop-table-card {
    display: none;
  }
}
</style>
