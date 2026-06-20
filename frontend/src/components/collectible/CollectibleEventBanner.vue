<template>

  <div v-if="events.length" class="event-zone">

    <div v-for="ev in events" :key="ev.code" class="event-banner glass-panel">

      <div class="event-glow" aria-hidden="true" />

      <div class="event-content">

        <div class="event-head">

          <span class="event-tag">限时活动</span>

          <h3>{{ ev.name }}</h3>

        </div>

        <p v-if="ev.description" class="event-desc">{{ ev.description }}</p>

        <ul class="event-perks">

          <li>活动应援 {{ ev.coin_action_cost }} 球迷币 · 每日每队 1 次</li>

          <li>比赛日动员同样加权掉落限定卡</li>

        </ul>

        <div class="event-actions">

          <el-button

            type="primary"

            size="default"

            :loading="loading"

            :disabled="!teamId"

            @click="$emit('cheer', teamId!)"

          >

            {{ teamId ? `为${teamName}应援` : '设置主队后可应援' }}

          </el-button>

          <router-link v-if="!teamId" to="/onboarding" class="setup-link">去设置主队</router-link>

        </div>

      </div>

    </div>

  </div>

</template>



<script setup lang="ts">

import { computed, onMounted } from 'vue'

import type { CollectibleEventBrief } from '@/api/collectionPass'

import { authState } from '@/stores/authStore'

import { fetchProfileStatus, profileState } from '@/stores/profileStore'



const props = defineProps<{

  events?: CollectibleEventBrief[] | null

  event?: CollectibleEventBrief | null

  loading?: boolean

}>()



defineEmits<{ cheer: [teamId: number] }>()



const events = computed(() => {

  if (props.events?.length) return props.events

  if (props.event) return [props.event]

  return []

})



const teamId = computed(() => authState.user?.favorite_team_id ?? null)

const teamName = computed(() => profileState.status?.main_team?.name || '主队')

onMounted(() => {
  if (teamId.value) void fetchProfileStatus()
})

</script>



<style scoped>

.event-zone {

  display: flex;

  flex-direction: column;

  gap: 10px;

  margin-bottom: 14px;

}



.event-banner {

  position: relative;

  overflow: hidden;

  padding: 0;

  border: 1px solid rgba(126, 184, 255, 0.3);

  border-radius: 14px;

}



.event-glow {

  position: absolute;

  inset: -40% -20% auto auto;

  width: 120px;

  height: 120px;

  background: radial-gradient(circle, rgba(126, 184, 255, 0.25), transparent 70%);

  pointer-events: none;

}



.event-content {

  position: relative;

  padding: 14px 16px;

}



.event-head {

  display: flex;

  align-items: center;

  gap: 8px;

  margin-bottom: 6px;

}



.event-tag {

  font-size: 0.65rem;

  padding: 2px 8px;

  border-radius: 999px;

  background: rgba(126, 184, 255, 0.18);

  color: #7eb8ff;

  font-weight: 600;

}



.event-head h3 {

  margin: 0;

  font-size: 1.02rem;

  color: #f5f0e8;

}



.event-desc {

  margin: 0 0 8px;

  font-size: 0.8rem;

  color: var(--wc-text-muted);

  line-height: 1.45;

}



.event-perks {

  margin: 0 0 12px;

  padding-left: 1.1em;

  font-size: 0.75rem;

  color: var(--wc-text-muted);

  line-height: 1.5;

}



.event-actions {

  display: flex;

  flex-wrap: wrap;

  align-items: center;

  gap: 10px;

}



.setup-link {

  font-size: 0.78rem;

  color: #7eb8ff;

  text-decoration: none;

}



.setup-link:hover {

  text-decoration: underline;

}

</style>

