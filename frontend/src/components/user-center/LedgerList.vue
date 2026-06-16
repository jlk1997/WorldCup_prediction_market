<template>
  <div class="ledger-list">
    <div v-if="isMobile" class="mobile-list">
      <article v-for="row in rows" :key="rowKey(row)" class="ledger-card">
        <slot name="mobile" :row="row" />
      </article>
      <p v-if="!rows.length" class="empty-text">{{ emptyText }}</p>
    </div>
    <div v-else class="table-scroll-wrap">
      <el-table :data="rows" size="small" :empty-text="emptyText" class="ledger-table">
        <el-table-column
          v-for="col in columns"
          :key="col.prop || col.slot || col.label"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
        >
          <template v-if="col.slot" #default="{ row }">
            <slot :name="col.slot" :row="row" />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useBreakpoint } from '../../composables/useBreakpoint'

defineProps<{
  rows: any[]
  columns: Array<{
    prop?: string
    label: string
    width?: number | string
    minWidth?: number | string
    slot?: string
  }>
  emptyText?: string
  rowKeyField?: string
}>()

const { isMobile } = useBreakpoint()

function rowKey(row: any) {
  return String(row.id ?? row.match_id ?? JSON.stringify(row))
}
</script>

<style scoped>
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ledger-card {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.22);
  background: rgba(10, 12, 24, 0.92);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.empty-text {
  text-align: center;
  color: var(--wc-text-muted);
  font-size: 0.88rem;
  padding: 28px 12px;
  border-radius: 12px;
  border: 1px dashed rgba(212, 165, 116, 0.25);
  background: rgba(10, 12, 24, 0.55);
}

.table-scroll-wrap {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.18);
  background: rgba(10, 12, 24, 0.88);
}

.ledger-table :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(212, 165, 116, 0.08);
  --el-table-row-hover-bg-color: rgba(212, 165, 116, 0.06);
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-text-color: rgba(255, 255, 255, 0.88);
  --el-table-header-text-color: rgba(240, 217, 181, 0.92);
}

.ledger-table :deep(.el-table__empty-text) {
  color: var(--wc-text-muted);
}

/* 插槽内容样式（父组件 template 里的 class 也生效） */
.ledger-card :deep(.ledger-card-head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.ledger-card :deep(.ledger-delta) {
  font-size: 1.35rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  line-height: 1;
}

.ledger-card :deep(.ledger-delta.plus) {
  color: #8fd48a;
}

.ledger-card :deep(.ledger-delta.minus) {
  color: #f89898;
}

.ledger-card :deep(.ledger-time) {
  flex-shrink: 0;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.48);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.ledger-card :deep(.ledger-reason) {
  margin: 0 0 10px;
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.45;
  color: #f5f0e8;
}

.ledger-card :deep(.ledger-balance) {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.ledger-card :deep(.ledger-title) {
  display: block;
  margin: 0 0 6px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #f5f0e8;
}

.ledger-card :deep(.predict-match) {
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.4;
  color: #f5f0e8;
  margin-bottom: 10px;
}

.ledger-card :deep(.predict-meta) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.ledger-card :deep(.predict-chip) {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.78);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.ledger-card :deep(.predict-chip.status-won) {
  color: #8fd48a;
  border-color: rgba(143, 212, 138, 0.35);
  background: rgba(103, 194, 58, 0.12);
}

.ledger-card :deep(.predict-chip.status-lost) {
  color: #f89898;
  border-color: rgba(248, 152, 152, 0.35);
  background: rgba(245, 108, 108, 0.1);
}

.ledger-card :deep(.predict-chip.status-void) {
  color: #79bbff;
  border-color: rgba(121, 187, 255, 0.35);
  background: rgba(64, 158, 255, 0.1);
}

.ledger-card :deep(.predict-chip.status-pending) {
  color: #e6a23c;
  border-color: rgba(230, 162, 60, 0.35);
  background: rgba(230, 162, 60, 0.1);
}

.ledger-card :deep(.predict-footer) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.58);
}

.ledger-card :deep(.predict-footer .plus) {
  color: #8fd48a;
  font-weight: 700;
}

.ledger-card :deep(.predict-footer .redeem-pts) {
  color: var(--wc-accent-rose);
  font-weight: 700;
}

.ledger-card :deep(.plus) {
  color: #8fd48a;
  font-weight: 700;
}

.ledger-card :deep(.minus) {
  color: #f89898;
  font-weight: 700;
}

.ledger-card :deep(.redeem-pts) {
  color: var(--wc-accent-rose);
  font-weight: 700;
}

.ledger-card :deep(.return-coins) {
  color: #6ec99a;
  margin-left: 4px;
}
</style>
