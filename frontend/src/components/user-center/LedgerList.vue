<template>
  <div class="ledger-list">
    <div v-if="isMobile" class="mobile-list">
      <div v-for="row in rows" :key="rowKey(row)" class="ledger-card glass-inner">
        <slot name="mobile" :row="row" />
      </div>
      <p v-if="!rows.length" class="empty-text">{{ emptyText }}</p>
    </div>
    <div v-else class="table-scroll-wrap">
      <el-table :data="rows" size="small" :empty-text="emptyText">
        <el-table-column
          v-for="col in columns"
          :key="col.prop"
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
  gap: 10px;
}

.ledger-card {
  padding: 12px 14px;
  border-radius: 10px;
}

.empty-text {
  text-align: center;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
  padding: 16px 0;
}

.plus {
  color: #67c23a;
  font-weight: 600;
}

.minus {
  color: #f56c6c;
  font-weight: 600;
}

.redeem-pts {
  color: var(--wc-accent-rose);
  font-weight: 600;
}

.return-coins {
  color: #6ec99a;
  margin-left: 4px;
}

.ledger-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.ledger-time {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.ledger-reason {
  margin: 0 0 4px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.85);
}

.ledger-balance {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}

.ledger-title {
  display: block;
  color: #f5f0e8;
  margin-bottom: 4px;
}

.predict-match {
  font-weight: 700;
  color: #f5f0e8;
  margin-bottom: 6px;
}

.predict-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}

.predict-footer {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}
</style>
