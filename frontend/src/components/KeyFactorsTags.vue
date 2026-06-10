<template>
  <div class="key-factors" v-if="factors.length">
    <h4 v-if="title">{{ title }}</h4>
    <div class="tags">
      <el-tag
        v-for="(f, i) in factors"
        :key="i"
        :type="tagType(i)"
        effect="dark"
        class="factor-tag"
      >{{ f }}</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ items?: string[]; title?: string }>(), {
  title: '关键因素',
})

const factors = computed(() => (props.items || []).filter(Boolean))

function tagType(i: number): 'primary' | 'success' | 'info' | 'warning' | 'danger' | undefined {
  const types: Array<'primary' | 'success' | 'warning' | 'info' | undefined> = [undefined, 'success', 'warning', 'info']
  return types[i % types.length]
}
</script>

<style scoped>
.key-factors h4 { margin: 0 0 10px; color: #D2A76D; }
.tags { display: flex; flex-wrap: wrap; gap: 8px; }
.factor-tag { max-width: 100%; white-space: normal; height: auto; padding: 6px 10px; line-height: 1.3; }
</style>
