<template>
  <div class="team-picker">
    <el-input v-model="searchInput" placeholder="搜索球队（全组检索）" clearable class="search" />

    <div v-if="isSearching" class="search-results">
      <p v-if="!searchResults.length" class="empty-hint">未找到「{{ searchInput.trim() }}」相关球队</p>
      <div v-else class="grid">
        <button
          v-for="t in searchResults"
          :key="t.id"
          type="button"
          class="team-card"
          :class="{ selected: modelValue === t.id, disabled: excludeId === t.id }"
          :disabled="excludeId === t.id"
          @click="select(t.id)"
        >
          <span class="name">{{ t.name }}</span>
          <span class="meta">{{ t.group_name ? `组 ${t.group_name}` : '-' }}</span>
        </button>
      </div>
    </div>

    <el-tabs v-else v-model="activeGroup" class="group-tabs tabs-scroll">
      <el-tab-pane v-for="g in groups" :key="g" :label="`组 ${g}`" :name="g">
        <div class="grid">
          <button
            v-for="t in teamsByGroup(g)"
            :key="t.id"
            type="button"
            class="team-card"
            :class="{ selected: modelValue === t.id, disabled: excludeId === t.id }"
            :disabled="excludeId === t.id"
            @click="select(t.id)"
          >
            <span class="name">{{ t.name }}</span>
            <span class="meta">{{ t.group_name ? `组 ${t.group_name}` : '-' }}</span>
          </button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { TeamBrief } from '../api/profile'

const props = defineProps<{
  teams: TeamBrief[]
  modelValue: number | null
  excludeId?: number | null
}>()

const emit = defineEmits<{ 'update:modelValue': [number] }>()

const searchInput = ref('')
const search = ref('')
const activeGroup = ref('A')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(searchInput, (v) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    search.value = v
  }, 300)
})

const groups = computed(() => {
  const set = new Set(props.teams.map((t) => t.group_name || '?'))
  return Array.from(set).sort()
})

const isSearching = computed(() => !!search.value.trim())

const searchResults = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return []
  return props.teams.filter((t) => t.name.toLowerCase().includes(q))
})

watch(
  groups,
  (g) => {
    if (g.length && !g.includes(activeGroup.value)) {
      activeGroup.value = g[0]
    }
  },
  { immediate: true },
)

watch(
  () => props.modelValue,
  (id) => {
    if (isSearching.value || !id) return
    const team = props.teams.find((t) => t.id === id)
    if (team?.group_name) activeGroup.value = team.group_name
  },
)

function teamsByGroup(g: string) {
  return props.teams.filter((t) => (t.group_name || '?') === g)
}

function select(id: number) {
  emit('update:modelValue', id)
  const team = props.teams.find((t) => t.id === id)
  if (team?.group_name) activeGroup.value = team.group_name
}
</script>

<style scoped>
.search {
  margin-bottom: 12px;
}

.search-results {
  margin-top: 4px;
}

.empty-hint {
  margin: 8px 0 0;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  text-align: center;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
}

.team-card {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  text-align: left;
  color: var(--wc-text-primary);
  transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.team-card:hover:not(.disabled) {
  transform: translateY(-2px);
}

.team-card.selected {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.15);
  box-shadow: 0 0 16px rgba(212, 165, 116, 0.2);
}

.team-card.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.name {
  display: block;
  font-weight: 600;
  font-size: 0.9rem;
}

.meta {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}

@media (max-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-height: min(50vh, 420px);
  }
  .team-card {
    min-height: 56px;
    padding: 10px;
  }
  .name {
    font-size: 0.82rem;
    white-space: normal;
    line-height: 1.25;
  }
}
</style>
