<template>

  <div v-if="!dismissed" class="banner glass-panel" :class="{ 'banner--dashboard': isDashboard }">

    <span class="banner-text">完善球迷档案，解锁助威、个性化大屏与主队竞猜高亮</span>

    <div class="actions">

      <el-button type="primary" size="small" class="mobile-full-btn" @click="$router.push('/onboarding')">去完善</el-button>

      <el-button text size="small" @click="dismiss">稍后</el-button>

    </div>

  </div>

</template>



<script setup lang="ts">

import { ref } from 'vue'

import { useRoute } from 'vue-router'



const emit = defineEmits<{ dismiss: [] }>()



const KEY = 'wc_skip_profile_banner'

const dismissed = ref(false)

const route = useRoute()

const isDashboard = ref(route.path === '/')



function dismiss() {

  dismissed.value = true

  localStorage.setItem(KEY, '1')

  emit('dismiss')

}

</script>



<style scoped>

.banner {

  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 12px;

  padding: 10px 16px;

  margin: 12px 16px 0;

  font-size: 0.85rem;

  flex-wrap: wrap;

  pointer-events: auto;

}

.banner--dashboard {

  margin: 8px 12px 0;

  position: relative;

  z-index: 30;

}

.banner-text {

  flex: 1;

  min-width: 0;

  line-height: 1.45;

}

.actions {

  display: flex;

  gap: 8px;

  flex-shrink: 0;

}



@media (max-width: 768px) {

  .banner {

    flex-direction: column;

    align-items: stretch;

    margin: 8px 10px 0;

    padding: 10px 12px;

  }

  .actions {

    flex-direction: column;

    width: 100%;

  }

  .actions .el-button {

    width: 100%;

    min-height: 40px;

    margin-left: 0 !important;

  }

}

</style>

