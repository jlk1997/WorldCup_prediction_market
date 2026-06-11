<template>
  <div class="uc-settings glass-panel">
    <section class="settings-block">
      <h2>账户设置</h2>
      <div class="nick-row">
        <el-input v-model="nickname" placeholder="新昵称" maxlength="20" />
        <el-button plain :loading="loading" @click="submit">修改昵称（20 币/次）</el-button>
      </div>
    </section>

    <section class="settings-block">
      <h2>偏好</h2>
      <p class="hint">设置主队、副队与心仪球星，获得更精准的推荐与问答。</p>
      <el-button type="primary" plain @click="$router.push('/onboarding')">编辑球队偏好</el-button>
    </section>

    <section class="settings-block">
      <el-button type="danger" plain class="logout-btn" @click="$emit('logout')">退出登录</el-button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  logout: []
  'change-nickname': [name: string]
}>()

const nickname = ref('')

function submit() {
  emit('change-nickname', nickname.value.trim())
  nickname.value = ''
}
</script>

<style scoped>
.uc-settings {
  padding: 18px 16px;
}

.settings-block {
  margin-bottom: 24px;
}

.settings-block:last-child {
  margin-bottom: 0;
}

.settings-block h2 {
  margin: 0 0 12px;
  font-size: 1rem;
  font-weight: 700;
  color: #f0d9b5;
}

.hint {
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}

.nick-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.logout-btn {
  width: 100%;
  min-height: 44px;
}

@media (max-width: 768px) {
  .nick-row {
    flex-direction: column;
    align-items: stretch;
  }

  .nick-row .el-input {
    width: 100%;
  }

  .nick-row .el-button {
    width: 100%;
    min-height: 44px;
  }
}
</style>
