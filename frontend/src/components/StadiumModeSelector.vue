<template>
  <el-dropdown trigger="click" @command="onSelect">
    <span class="mode-trigger">
      <span class="mode-label-long">3D: {{ label }}</span>
      <span class="mode-label-short">3D</span>
      <el-icon><ArrowDown /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="auto">自动</el-dropdown-item>
        <el-dropdown-item command="high">高画质</el-dropdown-item>
        <el-dropdown-item command="balanced">均衡</el-dropdown-item>
        <el-dropdown-item command="lite">轻量（无3D）</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { useStadiumStore, type PerformanceMode } from '@/stores/stadiumStore'

const { performanceMode, effectiveMode, setPerformanceMode } = useStadiumStore()

const labels: Record<PerformanceMode, string> = {
  auto: '自动',
  high: '高',
  balanced: '均衡',
  lite: '轻量',
}

const label = computed(() => {
  if (performanceMode.value === 'auto') {
    return `自动(${labels[effectiveMode.value]})`
  }
  return labels[performanceMode.value]
})

function onSelect(cmd: string) {
  setPerformanceMode(cmd as PerformanceMode)
}
</script>

<style scoped>
.mode-trigger {
  color: var(--wc-text-muted);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 16px;
  white-space: nowrap;
}
.mode-trigger:hover { color: var(--wc-accent-gold); }

@media (max-width: 960px) {
  .mode-trigger {
    font-size: 12px;
    margin-right: 4px;
  }
  .mode-label-long { display: none; }
}

@media (min-width: 961px) {
  .mode-label-short { display: none; }
}
</style>
