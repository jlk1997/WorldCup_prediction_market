<template>
  <div class="mint-page">
    <div class="page-header">
      <h1>首发打新</h1>
      <p class="subtitle">限量发行 · 序列号稀缺 · 错过即绝版。球星卡为站内虚拟藏品，无现金价值、不可提现</p>
    </div>

    <div v-if="loading" class="mint-list">
      <el-skeleton v-for="i in 3" :key="i" :rows="4" animated class="sk-card" />
    </div>
    <div v-else-if="!events.length" class="empty-state glass-inner">
      <p>暂无打新活动</p>
      <span>新赛事限量球星卡即将开售，敬请关注</span>
    </div>
    <div v-else class="mint-list">
      <div v-for="ev in events" :key="ev.id" class="mint-card glass-inner" :class="[ev.rarity, { collab: isCollab(ev) }]">
        <div class="mint-banner" :style="ev.image_url ? { backgroundImage: `url(${ev.image_url})` } : {}">
          <span class="phase" :class="ev.phase">{{ phaseLabel(ev) }}</span>
          <span v-if="isCollab(ev)" class="collab-tag">联名/IP</span>
          <span v-else-if="ev.competition" class="comp">{{ ev.competition }}</span>
        </div>
        <div class="mint-body">
          <div class="title-row">
            <h3>{{ ev.name }}</h3>
            <span class="rarity" :class="ev.rarity">{{ rarityLabel(ev.rarity) }}</span>
          </div>
          <p class="desc">{{ ev.description }}</p>

          <div class="time-row">
            <span v-if="ev.phase === 'scheduled' && ev.reserve_starts_at" class="time-chip">
              {{ timeUntil(ev.reserve_starts_at, '预约开启') }}
            </span>
            <span v-else-if="ev.phase === 'reserving'" class="time-chip reserving">
              {{ timeUntil(ev.starts_at, '开售') }}
            </span>
            <span v-else-if="ev.phase === 'live'" class="time-chip live">
              {{ timeUntil(ev.ends_at, '结束') }}
            </span>
            <span v-if="ev.per_user_limit" class="limit-chip">限购 {{ ev.per_user_limit }} 张/人</span>
          </div>

          <div class="supply">
            <div class="supply-bar">
              <div class="supply-fill" :style="{ width: `${(ev.issued / ev.total_supply) * 100}%` }" />
            </div>
            <div class="supply-meta">
              <span>已发行 {{ ev.issued }} / {{ ev.total_supply }}</span>
              <span class="remain">剩余 {{ ev.remaining }}</span>
            </div>
          </div>

          <div class="mint-foot">
            <div class="price">
              <template v-if="ev.currency === 'coins'">
                <b>{{ ev.price_coins }}</b><span>球迷币</span>
              </template>
              <template v-else>
                <b class="rmb-muted">¥{{ (ev.price_fen / 100).toFixed(2) }}</b><span class="rmb-muted">人民币首发</span>
                <span class="coming-soon">即将开放</span>
              </template>
              <span class="mode-tag">{{ modeLabel(ev.sale_mode) }}</span>
            </div>
            <div class="actions">
              <el-button
                v-if="ev.phase === 'reserving' || (ev.phase === 'scheduled' && ev.sale_mode !== 'public')"
                size="small"
                :type="ev.reserved ? 'success' : 'primary'"
                plain
                :disabled="ev.reserved"
                :loading="actingId === ev.id"
                @click="doReserve(ev)"
              >
                {{ ev.reserved ? '已预约' : '预约/报名' }}
              </el-button>
              <el-button
                v-if="ev.phase === 'live' && ev.currency === 'coins'"
                size="small"
                type="primary"
                :disabled="!ev.can_buy || ev.remaining <= 0"
                :loading="actingId === ev.id"
                @click="doPurchase(ev)"
              >
                {{ purchaseLabel(ev) }}
              </el-button>
              <el-button
                v-else-if="ev.phase === 'live' && ev.currency !== 'coins'"
                size="small"
                disabled
              >
                即将开放
              </el-button>
              <span v-if="ev.phase === 'sold_out'" class="soldout">已售罄</span>
              <span v-if="ev.phase === 'ended'" class="ended">已结束</span>
            </div>
          </div>
          <p v-if="ev.currency === 'rmb'" class="rmb-alt">可先参与球迷币场次，或预约等待人民币通道开放</p>
          <div v-if="ev.sale_mode === 'lottery' && ev.reserved && ev.reservation_status === 'reserved'" class="lottery-note pending">
            已报名，等待抽签结果…
          </div>
          <div v-else-if="ev.reservation_status === 'lost'" class="lottery-note lost">很遗憾未中签</div>
          <div v-else-if="ev.reservation_status === 'won'" class="lottery-note won">恭喜中签，快去打新！</div>
        </div>
      </div>
    </div>

    <p class="disclaimer">
      一级限量发行属合规数字藏品发售；二级流通仅支持站内可用积分计价，平台不支持人民币二级交易与提现。
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMintEvents, reserveMint, purchaseMint, type MintEvent } from '@/api/asset'
import { fetchMe } from '@/stores/authStore'
import { extractApiError } from '@/utils/apiError'
import { usePageMeta } from '@/composables/usePageMeta'
import { useCountdownTick, formatTimeUntil } from '@/composables/useCountdown'

usePageMeta({
  title: '首发打新 — 最后一舞',
  description: '限量球星卡首发打新，序列号稀缺。站内虚拟藏品，无现金价值。',
  path: '/mint',
  noIndex: true,
})

const tick = useCountdownTick()
const loading = ref(false)
const events = ref<MintEvent[]>([])
const actingId = ref<number | null>(null)

const RARITY: Record<string, string> = { common: '普通', rare: '稀有', epic: '史诗', legend: '传奇' }
const MODE: Record<string, string> = { public: '公开发售', whitelist: '白名单', lottery: '抽签' }
const PHASE: Record<string, string> = {
  scheduled: '未开始',
  reserving: '预约中',
  live: '发售中',
  sold_out: '已售罄',
  ended: '已结束',
}
function rarityLabel(r: string) {
  return RARITY[r] || r
}
function modeLabel(m: string) {
  return MODE[m] || m
}
function phaseLabel(ev: MintEvent) {
  return PHASE[ev.phase] || ev.phase
}
function timeUntil(iso?: string | null, prefix = '还剩') {
  void tick.value
  return formatTimeUntil(iso, prefix)
}
function purchaseLabel(ev: MintEvent) {
  if (ev.currency !== 'coins') return '即将开放'
  if (ev.remaining <= 0) return '已售罄'
  if (ev.sale_mode === 'lottery' && ev.reservation_status !== 'won') return '待中签'
  if (ev.sale_mode === 'whitelist' && !ev.reserved) return '需预约'
  return '立即打新'
}

function isCollab(ev: MintEvent) {
  return ev.competition === 'Collab2026' || ev.code.startsWith('mint_collab_')
}

async function load() {
  loading.value = true
  try {
    events.value = await getMintEvents()
  } finally {
    loading.value = false
  }
}

async function doReserve(ev: MintEvent) {
  actingId.value = ev.id
  try {
    await reserveMint(ev.id)
    ElMessage.success('预约成功，开售/开奖后将通知你')
    await load()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '预约失败'))
  } finally {
    actingId.value = null
  }
}

async function doPurchase(ev: MintEvent) {
  try {
    await ElMessageBox.confirm(
      ev.currency === 'coins'
        ? `确认消耗 ${ev.price_coins} 球迷币打新「${ev.name}」？`
        : `确认以 ¥${(ev.price_fen / 100).toFixed(2)} 打新「${ev.name}」？`,
      '首发打新',
      { customClass: 'wc-message-box', roundButton: true, confirmButtonText: '确认打新', cancelButtonText: '再想想' },
    )
  } catch {
    return
  }
  actingId.value = ev.id
  try {
    const res = await purchaseMint(ev.id)
    ElMessage.success(`${res.notice} 序列号 #${res.serial_no ?? '—'}`)
    await fetchMe()
    await load()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '打新失败'))
  } finally {
    actingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.mint-page {
  max-width: 760px;
  margin: 0 auto;
  padding-bottom: calc(var(--wc-bottom-nav-height, 56px) + 24px);
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 1.5rem;
  color: var(--wc-accent-gold);
}
.subtitle {
  margin: 0 0 16px;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.mint-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mint-card {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(212, 165, 116, 0.2);
}
.mint-card.legend { border-color: rgba(231, 175, 92, 0.5); }
.mint-card.epic { border-color: rgba(168, 120, 224, 0.4); }
.mint-card.collab {
  border-color: rgba(255, 120, 180, 0.55);
  box-shadow: 0 0 24px rgba(255, 100, 160, 0.12);
}
.collab-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(255, 120, 180, 0.85), rgba(168, 120, 224, 0.85));
  color: #fff;
}
.rmb-muted { opacity: 0.55; }
.rmb-alt {
  margin: 6px 0 0;
  font-size: 0.66rem;
  color: var(--wc-text-muted);
  line-height: 1.35;
}
.coming-soon {
  margin-left: 8px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}
.mint-banner {
  position: relative;
  height: 130px;
  background: linear-gradient(135deg, rgba(40, 30, 20, 0.7), rgba(20, 16, 32, 0.95));
  background-size: cover;
  background-position: center;
}
.phase {
  position: absolute;
  top: 10px;
  left: 10px;
  font-size: 0.7rem;
  padding: 3px 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.55);
  color: #f0d9b5;
}
.phase.live {
  background: linear-gradient(90deg, #c0392b, #e74c3c);
  color: #fff;
  animation: pulse 1.6s infinite;
}
.phase.reserving { background: rgba(46, 134, 193, 0.85); color: #fff; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.comp {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 0.66rem;
  padding: 3px 8px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.5);
  color: var(--wc-text-secondary);
}
.mint-body {
  padding: 14px 16px 16px;
}
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.title-row h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--wc-text-secondary);
}
.rarity {
  font-size: 0.66rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
}
.rarity.legend { background: linear-gradient(90deg, #b8860b, #e7af5c); color: #1a1208; }
.rarity.epic { background: rgba(138, 80, 184, 0.85); color: #fff; }
.desc {
  margin: 6px 0 8px;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}
.time-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.time-chip {
  font-size: 0.72rem;
  padding: 3px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
}
.time-chip.reserving { color: #6eb5e0; }
.time-chip.live { color: #f0b86c; }
.limit-chip {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
}
.supply-bar {
  height: 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.supply-fill {
  height: 100%;
  background: linear-gradient(90deg, #d4a574, #e7af5c);
  transition: width 0.4s;
}
.supply-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  font-size: 0.7rem;
  color: var(--wc-text-muted);
}
.supply-meta .remain {
  color: #f0b86c;
}
.mint-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  gap: 10px;
}
.price {
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex-wrap: wrap;
}
.price b {
  font-size: 1.3rem;
  color: var(--wc-accent-gold);
  font-variant-numeric: tabular-nums;
}
.price span {
  font-size: 0.7rem;
  color: var(--wc-text-muted);
}
.mode-tag {
  margin-left: 6px;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  font-size: 0.62rem !important;
}
.soldout, .ended {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
}
.lottery-note {
  margin-top: 10px;
  font-size: 0.75rem;
  padding: 6px 10px;
  border-radius: 8px;
}
.lottery-note.pending { background: rgba(110, 181, 224, 0.12); color: #6eb5e0; }
.lottery-note.won { background: rgba(46, 160, 100, 0.15); color: #5fc88f; }
.lottery-note.lost { background: rgba(160, 70, 70, 0.12); color: #e07a7a; }
.empty-state {
  text-align: center;
  padding: 40px 20px;
  border-radius: 12px;
  color: var(--wc-text-muted);
}
.empty-state p {
  margin: 0 0 6px;
  font-size: 1rem;
  color: var(--wc-text-secondary);
}
.disclaimer {
  margin-top: 20px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
  text-align: center;
}
.sk-card {
  padding: 14px;
  border-radius: 12px;
  background: rgba(20, 24, 42, 0.4);
}
</style>
