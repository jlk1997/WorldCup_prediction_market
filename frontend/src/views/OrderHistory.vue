<template>
  <div class="orders-page has-bottom-nav">
    <div class="page-header">
      <h1>我的订单</h1>
      <p class="subtitle">现金支付记录 · 含球星卡打新与商城充值</p>
    </div>

    <div v-if="loading" class="list">
      <el-skeleton v-for="i in 4" :key="i" :rows="3" animated class="sk" />
    </div>
    <div v-else-if="!orders.length" class="empty glass-inner">
      <p>暂无订单</p>
      <el-button type="primary" plain @click="goShop">去商城看看</el-button>
    </div>
    <div v-else class="list">
      <article v-for="o in orders" :key="o.id" class="order-card glass-inner">
        <div class="row-top">
          <strong>{{ o.product_name }}</strong>
          <span class="status" :class="o.status">{{ statusLabel(o.status) }}</span>
        </div>
        <div class="row-mid">
          <span>¥{{ (o.amount_fen / 100).toFixed(2) }}</span>
          <span class="type">{{ typeLabel(o.product_type) }}</span>
        </div>
        <ul v-if="o.grant_summary?.length" class="grants">
          <li v-for="(line, idx) in o.grant_summary" :key="idx">{{ line }}</li>
        </ul>
        <div class="row-foot">
          <span class="mono">{{ o.out_trade_no }}</span>
          <span>{{ formatTime(o.paid_at || o.created_at) }}</span>
        </div>
        <p v-if="o.product_type === 'mint_event' && o.status === 'paid' && o.mint_user_card_id" class="mint-chain-hint">
          打新卡牌 ·
          <router-link :to="`/collection?highlight=${o.mint_user_card_id}`">查看链上铸造进度</router-link>
        </p>
        <div v-if="o.status === 'pending'" class="actions">
          <el-button size="small" type="primary" plain @click="continuePay(o)">继续支付</el-button>
          <el-button size="small" :loading="cancellingId === o.id" @click="cancelOne(o)">取消</el-button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { cancelOrder, getProducts, listOrders, createOrder, type OrderDetail } from '@/api/commerce'
import { createMintOrder } from '@/api/asset'
import { extractApiError } from '@/utils/apiError'
import { usePageMeta } from '@/composables/usePageMeta'
import { PENDING_ORDER_KEY, resolvePayChannel } from '@/utils/payEnv'

usePageMeta({ title: '我的订单', path: '/shop/orders', noIndex: true })

const router = useRouter()
const loading = ref(false)
const orders = ref<OrderDetail[]>([])
const cancellingId = ref<number | null>(null)

const STATUS: Record<string, string> = {
  pending: '待支付',
  paid: '已支付',
  cancelled: '已取消',
  refunded: '已退款',
}
const TYPE: Record<string, string> = {
  mint_event: '球星卡打新',
  coins: '球迷币',
  season_pass: '赛季通行证',
  collection_pass: '藏品手册',
  cosmetic: '装扮',
}

function statusLabel(s: string) {
  return STATUS[s] || s
}
function typeLabel(t: string) {
  return TYPE[t] || t
}
function formatTime(iso?: string | null) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

async function load() {
  loading.value = true
  try {
    orders.value = await listOrders(40)
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

async function cancelOne(o: OrderDetail) {
  cancellingId.value = o.id
  try {
    await cancelOrder(o.out_trade_no)
    ElMessage.success('订单已取消')
    await load()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '取消失败'))
  } finally {
    cancellingId.value = null
  }
}

async function continuePay(o: OrderDetail) {
  try {
    if (o.product_type === 'mint_event' && o.mint_event_id) {
      const { order, pay_url } = await createMintOrder(o.mint_event_id, true, resolvePayChannel())
      sessionStorage.setItem(PENDING_ORDER_KEY, order.out_trade_no)
      window.location.href = pay_url
      return
    }
    const products = await getProducts()
    const product = products.find((p) => p.name === o.product_name)
    if (!product) {
      ElMessage.warning('请从商城重新选择商品')
      router.push('/shop')
      return
    }
    const { order, pay_url } = await createOrder(product.id, true, resolvePayChannel())
    sessionStorage.setItem(PENDING_ORDER_KEY, order.out_trade_no)
    window.location.href = pay_url
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '无法继续支付'))
  }
}

function goShop() {
  router.push('/shop')
}

onMounted(load)
</script>

<style scoped>
.orders-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 16px calc(var(--wc-bottom-nav-height, 56px) + 24px);
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 1.35rem;
  color: var(--wc-accent-gold);
}
.subtitle {
  margin: 0 0 16px;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.order-card {
  padding: 14px 16px;
  border-radius: 12px;
}
.row-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.row-top strong {
  color: var(--wc-text-secondary);
  font-size: 0.95rem;
}
.status {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
}
.status.paid {
  color: #67c23a;
}
.status.pending {
  color: #f0b86c;
}
.row-mid {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
  color: var(--wc-accent-gold);
  margin-bottom: 8px;
}
.type {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.grants {
  margin: 0 0 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(103, 194, 58, 0.08);
  list-style: none;
  font-size: 0.78rem;
  color: #d4edda;
}
.row-foot {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.mono {
  word-break: break-all;
  max-width: 58%;
}
.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
.mint-chain-hint {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.mint-chain-hint a {
  color: #7eb8ff;
  text-decoration: none;
}
.mint-chain-hint a:hover {
  text-decoration: underline;
}
.empty {
  text-align: center;
  padding: 40px 16px;
  border-radius: 12px;
}
.sk {
  padding: 14px;
  border-radius: 12px;
}
</style>
