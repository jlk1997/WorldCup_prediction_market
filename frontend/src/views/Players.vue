<template>

  <div class="players-container page-shell">

    <el-card class="box-card">

      <template #header>

        <div class="card-header">
          <div class="header-title-block">
            <span>球员库</span>
            <span class="sub-title">共 {{ totalCount }} 人 · 数据来自 sync_teams</span>
          </div>
          <el-input
            v-model="keyword"
            class="search-input"
            placeholder="搜索姓名 / 球队 / 俱乐部"
            clearable
            @input="onSearchInput"
          />
        </div>

      </template>



      <el-empty v-if="!loading && filtered.length === 0" :description="emptyText">
        <el-button v-if="totalCount === 0" type="primary" @click="reload">重新加载</el-button>
      </el-empty>

      <div v-else class="table-scroll-wrap">
        <el-table :data="pagedRows" class="players-table-compact" style="width: 100%" v-loading="loading">

        <el-table-column prop="name" label="球员姓名" width="160">

          <template #default="{ row }">

            <router-link :to="`/players/${row.id}`" class="player-link">{{ row.name }}</router-link>

          </template>

        </el-table-column>

        <el-table-column prop="team_name" label="所属球队" width="120" />

        <el-table-column prop="position" label="位置" width="100" />

        <el-table-column prop="age" label="年龄" width="70" />

        <el-table-column prop="is_key_player" label="首发" width="80">

          <template #default="{ row }">

            <el-tag :type="row.is_key_player ? 'success' : 'info'" size="small">

              {{ row.is_key_player ? '是' : '否' }}

            </el-tag>

          </template>

        </el-table-column>

        <el-table-column label="操作" width="100">

          <template #default="{ row }">

            <el-button size="small" @click="$router.push(`/players/${row.id}`)">详情</el-button>

          </template>

        </el-table-column>
      </el-table>
      <div class="pager-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="filtered.length"
          layout="prev, pager, next, total"
          background
          small
        />
      </div>
      </div>

    </el-card>

  </div>

</template>



<script setup lang="ts">

import { ref, computed, onMounted } from 'vue'

import { ElMessage } from 'element-plus'

import { apiClient } from '@/api/client'

import type { PlayerBrief } from '@/types/api'



const loading = ref(false)

const tableData = ref<PlayerBrief[]>([])

const keyword = ref('')
const page = ref(1)
const pageSize = 50

let searchTimer: ReturnType<typeof setTimeout> | null = null



const totalCount = computed(() => tableData.value.length)



const filtered = computed(() => {

  const q = keyword.value.trim().toLowerCase()

  if (!q) return tableData.value

  return tableData.value.filter(

    (p: PlayerBrief) =>

      p.name.toLowerCase().includes(q) ||

      (p.team_name || '').toLowerCase().includes(q),

  )

})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})



const emptyText = computed(() => {

  if (totalCount.value === 0) {

    return '库里还没有球员数据，请在后端执行：python -m scripts.sync_teams --source all'

  }

  if (keyword.value.trim()) {

    return `没有找到「${keyword.value.trim()}」相关球员，试试搜球队名或球员姓名`

  }

  return '暂无数据'

})



async function loadPlayers(search?: string) {

  loading.value = true

  try {

    const res = await apiClient.get<PlayerBrief[]>('/api/players', {

      params: { limit: 2000, q: search || undefined },

    })

    tableData.value = res.data

  } catch {

    ElMessage.error('获取球员数据失败，请确认后端已启动')

  } finally {

    loading.value = false

  }

}



function onSearchInput() {

  if (searchTimer) clearTimeout(searchTimer)

  page.value = 1

  searchTimer = setTimeout(() => {

    loadPlayers(keyword.value.trim() || undefined)

  }, 300)

}



function reload() {

  loadPlayers(keyword.value.trim() || undefined)

}



onMounted(() => loadPlayers())

</script>



<style scoped>
.players-container { max-width: 1200px; margin: 0 auto; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  color: var(--wc-text-primary);
  font-weight: 600;
  flex-wrap: wrap;
}
.header-title-block { display: flex; flex-direction: column; gap: 4px; }
.search-input { width: 260px; }
.sub-title {
  font-size: 12px;
  color: var(--wc-text-muted);
  font-weight: 400;
}
.player-link { color: var(--wc-accent-gold-light); text-decoration: none; font-weight: 600; }
.player-link:hover { color: #f5d9a8; text-decoration: underline; }
.pager-wrap { display: flex; justify-content: center; margin-top: 16px; }

@media (max-width: 768px) {
  .card-header { flex-direction: column; align-items: stretch; }
  .search-input { width: 100% !important; }
}
</style>


