<template>

  <section v-if="data" class="today-home glass-panel">

    <header class="today-head">

      <h2>今日主场</h2>

      <span class="ritual-chip">{{ data.ritual_done }}/{{ data.ritual_total }} 日常</span>

    </header>

    <div class="quick-nav">

      <button type="button" class="quick-link" @click="$router.push('/predict')">竞猜</button>

      <button type="button" class="quick-link" @click="$router.push('/agent')">AI</button>

      <button type="button" class="quick-link" @click="$router.push('/mint')">打新</button>

      <button type="button" class="quick-link" @click="$router.push('/market')">交易行</button>

    </div>

    <div

      v-if="data.matchday_offer"

      class="matchday-offer"

      role="button"

      tabindex="0"

      @click="go(data.matchday_offer.path)"

      @keydown.enter="go(data.matchday_offer.path)"

    >

      <span class="offer-tag">比赛日限定</span>

      <strong>{{ data.matchday_offer.title }}</strong>

      <p>{{ data.matchday_offer.body }}</p>

      <span v-if="data.matchday_offer.remaining > 0" class="offer-stock">

        余量 {{ data.matchday_offer.remaining }}

      </span>

    </div>



    <ChainAlertBanner

      v-if="data.failed_chain_mints || data.pending_chain_mints"

      :failed-count="data.failed_chain_mints"

      :pending-count="data.pending_chain_mints"

      :first-failed-user-card-id="data.first_failed_user_card_id"

      @retried="reload"

    />

    <ul v-if="data.todos?.length" class="todo-list">

      <li

        v-for="(t, i) in data.todos"

        :key="i"

        class="todo-item"

        role="button"

        tabindex="0"

        @click="go(t.path)"

        @keydown.enter="go(t.path)"

      >

        <span class="todo-kind">{{ kindLabel(t.kind) }}</span>

        <span class="todo-label">{{ t.label }}</span>

        <span class="todo-detail">{{ t.detail }}</span>

      </li>

    </ul>

    <p v-else class="empty">今日暂无待办，去竞猜大厅逛逛吧</p>

  </section>

</template>



<script setup lang="ts">

import { computed, onMounted, watch } from 'vue'

import { useRouter } from 'vue-router'

import { authState } from '@/stores/authStore'

import { fetchTodayHome, useTodayHomeRef } from '@/stores/todayHomeStore'

import { trackEvent } from '@/utils/analytics'

import ChainAlertBanner from '@/components/ChainAlertBanner.vue'



const router = useRouter()

const data = computed(() => useTodayHomeRef().value)



function kindLabel(kind: string) {

  const map: Record<string, string> = {

    predict: '竞猜',

    stake: '质押',

    duel: '对决',

    mint: '打新',

    chain: '链',

  }

  return map[kind] || kind

}



function go(path: string) {

  if (path.startsWith('/mint')) {

    trackEvent('matchday_offer_click', { path })

  }

  router.push(path)

}



async function reload() {

  await fetchTodayHome(true)

}



onMounted(() => {

  void fetchTodayHome()

})

watch(() => authState.user?.id, () => {

  void fetchTodayHome()

})

</script>



<style scoped>

.today-home {

  margin: 12px 0;

  padding: 14px 16px;

}

.today-head {

  display: flex;

  align-items: center;

  justify-content: space-between;

  margin-bottom: 10px;

}

.today-head h2 {

  margin: 0;

  font-size: 1rem;

}

.ritual-chip {

  font-size: 0.72rem;

  color: var(--wc-accent-gold);

}

.quick-nav {

  display: flex;

  gap: 8px;

  margin-bottom: 12px;

  flex-wrap: wrap;

}

.quick-link {

  border: 1px solid rgba(212, 165, 116, 0.35);

  background: rgba(212, 165, 116, 0.08);

  color: var(--wc-text-secondary);

  border-radius: 999px;

  padding: 4px 12px;

  font-size: 0.72rem;

  cursor: pointer;

}

.matchday-offer {

  margin-bottom: 12px;

  padding: 12px 14px;

  border-radius: 12px;

  background: linear-gradient(135deg, rgba(212, 100, 80, 0.15), rgba(212, 165, 116, 0.12));

  border: 1px solid rgba(212, 120, 90, 0.35);

  cursor: pointer;

}

.matchday-offer strong {

  display: block;

  font-size: 0.9rem;

  margin: 4px 0;

}

.matchday-offer p {

  margin: 0 0 6px;

  font-size: 0.78rem;

  color: var(--wc-text-muted);

  line-height: 1.4;

}

.offer-tag {

  font-size: 0.68rem;

  color: #e8a87c;

  text-transform: uppercase;

  letter-spacing: 0.04em;

}

.offer-stock {

  font-size: 0.72rem;

  color: var(--wc-accent-gold);

}

.todo-list {

  list-style: none;

  margin: 0;

  padding: 0;

  display: flex;

  flex-direction: column;

  gap: 8px;

}

.todo-item {

  display: grid;

  grid-template-columns: auto 1fr auto;

  gap: 8px;

  align-items: center;

  padding: 8px 10px;

  border-radius: 8px;

  background: rgba(255, 255, 255, 0.04);

  cursor: pointer;

}

.todo-kind {

  font-size: 0.68rem;

  color: var(--wc-accent-gold);

}

.todo-label {

  font-size: 0.82rem;

}

.todo-detail {

  font-size: 0.72rem;

  color: var(--wc-text-muted);

}

.empty {

  margin: 0;

  font-size: 0.82rem;

  color: var(--wc-text-muted);

}

</style>

