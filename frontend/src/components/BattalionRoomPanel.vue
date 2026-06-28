<template>
  <section v-if="room?.active" class="battalion-room glass-panel">
    <header class="br-head">
      <h3>军团 2.0 · {{ room.team_name }} 房间</h3>
      <span class="br-contrib">我的贡献 {{ room.my_contribution }}</span>
    </header>
    <div v-for="(g, i) in room.goals" :key="i" class="br-goal">
      <span class="br-type">{{ goalLabel(g.goal_type) }}</span>
      <div class="br-bar">
        <div
          class="br-fill"
          :style="{ width: `${Math.min(100, (g.current_value / Math.max(g.target_value, 1)) * 100)}%` }"
        />
      </div>
      <span class="br-num">{{ g.current_value }}/{{ g.target_value }}</span>
    </div>
    <button type="button" class="br-link" @click="$router.push('/arena')">去助威 / 竞猜冲贡献 →</button>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '@/api/client'
import { authState } from '@/stores/authStore'

interface Goal {
  goal_type: string
  target_value: number
  current_value: number
}

const room = ref<{
  active: boolean
  team_name: string
  my_contribution: number
  goals: Goal[]
} | null>(null)

function goalLabel(t: string) {
  const map: Record<string, string> = {
    predict_rate: '集体竞猜',
    cheer_total: '助威目标',
  }
  return map[t] || t
}

onMounted(async () => {
  if (!authState.user) return
  try {
    const res = await apiClient.get('/api/game/battalion-room')
    room.value = res.data
  } catch {
    room.value = null
  }
})
</script>

<style scoped>
.battalion-room {
  margin: 12px 0;
  padding: 14px 16px;
}
.br-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.br-head h3 {
  margin: 0;
  font-size: 0.92rem;
}
.br-contrib {
  font-size: 0.72rem;
  color: #8fd48a;
}
.br-goal {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.76rem;
}
.br-bar {
  height: 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
}
.br-fill {
  height: 100%;
  background: #58a6ff;
}
.br-num {
  color: var(--wc-text-muted);
  font-size: 0.68rem;
}
.br-link {
  margin-top: 8px;
  border: none;
  background: transparent;
  color: var(--wc-accent-gold);
  cursor: pointer;
  font-size: 0.75rem;
}
</style>
