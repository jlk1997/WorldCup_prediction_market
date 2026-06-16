<template>
  <div class="table-scroll-wrap">
  <el-table :data="rows" class="match-table-compact" style="width:100%">

    <el-table-column prop="group" label="小组" width="100" />

    <el-table-column prop="date" label="日期" width="120" />

    <el-table-column label="对阵">

      <template #default="{ row }">

        {{ row.team1 }} vs {{ row.team2 }}

      </template>

    </el-table-column>

    <el-table-column label="比分" width="100">

      <template #default="{ row }">

        <span v-if="row.home_score != null">{{ row.home_score }}:{{ row.away_score }}</span>

        <span v-else>-</span>

      </template>

    </el-table-column>

    <el-table-column prop="stadium" label="球场" />

    <el-table-column label="操作" width="220">

      <template #default="{ row }">

        <el-button v-if="row.id" size="small" link @click="goDetail(row)">详情</el-button>

        <el-button
          v-if="row.id && isMatchPredictable(row)"
          size="small"
          link
          @click="goPredict(row)"
        >
          竞猜
        </el-button>

        <el-button size="small" type="primary" @click="$emit('analyze', row)">{{ label(row) }}</el-button>

      </template>

    </el-table-column>

  </el-table>
  </div>
</template>



<script setup lang="ts">

import type { LiveMatch } from '@/types/api'

import { useAgentNavigate } from '@/composables/useAgentNavigate'

import { useRouter } from 'vue-router'

import { isMatchPredictable } from '@/utils/matchKickoff'



defineProps<{ rows: LiveMatch[] }>()

defineEmits<{ analyze: [row: LiveMatch] }>()



const router = useRouter()

const { goMatchDetail, agentButtonLabel } = useAgentNavigate()



function label(row: LiveMatch) {

  return agentButtonLabel(row)

}



function goDetail(row: LiveMatch) {

  goMatchDetail(row)

}

function goPredict(row: LiveMatch) {
  if (!row.id) return
  router.push({ path: '/predict', query: { highlight: String(row.id) } })
}

</script>


