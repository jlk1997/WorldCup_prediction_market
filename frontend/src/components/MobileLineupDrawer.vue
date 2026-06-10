<template>
  <el-drawer
    v-model="open"
    direction="btt"
    size="85%"
    :with-header="true"
    :title="drawerTitle"
    class="mobile-lineup-drawer"
    destroy-on-close
  >
    <el-tabs v-model="activeTab" class="lineup-tabs">
      <el-tab-pane :label="leftLabel" name="left">
        <TeamLineupColumn
          v-if="leftPanel"
          in-drawer
          :team-name="leftPanel.teamName"
          :tag-label="leftPanel.tagLabel"
          :tag-class="leftPanel.tagClass"
          :data="leftPanel.data"
          :loading="leftPanel.loading"
          :top-player="leftPanel.topPlayer"
          :lineup="leftPanel.lineup"
          :bench="leftPanel.bench"
          @header-click="$emit('team-click')"
        />
      </el-tab-pane>
      <el-tab-pane :label="rightLabel" name="right">
        <TeamLineupColumn
          v-if="rightPanel"
          in-drawer
          :team-name="rightPanel.teamName"
          :tag-label="rightPanel.tagLabel"
          :tag-class="rightPanel.tagClass"
          :data="rightPanel.data"
          :loading="rightPanel.loading"
          :top-player="rightPanel.topPlayer"
          :lineup="rightPanel.lineup"
          :bench="rightPanel.bench"
          @header-click="$emit('team-click')"
        />
      </el-tab-pane>
    </el-tabs>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import TeamLineupColumn from './TeamLineupColumn.vue'
import type { LineupPlayer } from './TeamLineupColumn.vue'

export type SidePanel = {
  teamName: string
  tagLabel: string
  tagClass: string
  data: Record<string, unknown> | null
  loading: boolean
  topPlayer: LineupPlayer | null
  lineup: LineupPlayer[]
  bench: LineupPlayer[]
}

const open = defineModel<boolean>({ default: false })

const props = defineProps<{
  leftPanel: SidePanel | null
  rightPanel: SidePanel | null
  matchLabel?: string
}>()

defineEmits<{ 'team-click': [] }>()

const activeTab = ref('left')

const drawerTitle = computed(() => props.matchLabel || '球队阵容')
const leftLabel = computed(() => props.leftPanel?.teamName || '主队')
const rightLabel = computed(() => props.rightPanel?.teamName || '客队')

watch(open, (v) => {
  if (v) activeTab.value = 'left'
})
</script>

<style scoped>
.lineup-tabs {
  height: 100%;
}

.lineup-tabs :deep(.el-tabs__content) {
  height: calc(100% - 44px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.lineup-tabs :deep(.lineup-column) {
  max-height: none;
}
</style>

<style>
.mobile-lineup-drawer .el-drawer__body {
  padding: 0 12px 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.mobile-lineup-drawer .el-drawer__header {
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(212, 165, 116, 0.15);
}
</style>
