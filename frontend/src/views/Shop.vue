<template>
  <div class="shop mobile-page">
    <div class="header glass-panel">
      <h1>球迷商城</h1>
      <p>充值球迷币 · 或用竞猜获得的可用积分兑换装扮与权益</p>
      <div v-if="authState.user" class="balances">
        <span><strong>{{ authState.user.fan_coins }}</strong> 球迷币</span>
        <span><strong>{{ authState.user.season_points }}</strong> 累计积分</span>
        <span class="redeem"><strong>{{ authState.user.redeem_points ?? 0 }}</strong> 可用积分</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="shop-tabs tabs-scroll">
      <el-tab-pane label="充值商城" name="cash">
        <div class="age-notice glass-panel">
          <span class="age-notice-badge">18+</span>
          <div class="age-notice-body">
            <strong>虚拟商品购买须知</strong>
            <p>充值球迷币为虚拟道具，购买后不可退款、不可提现。点击「购买」时将弹出确认窗口，需勾选同意后方可支付。</p>
          </div>
        </div>

        <div v-loading="loadingCash" class="products">
          <div
            v-for="p in cashProducts"
            :key="p.id"
            class="product glass-panel"
            :class="{ featured: p.featured, [`type-${p.product_type}`]: true }"
          >
            <div class="product-head">
              <h3>{{ p.name }}</h3>
              <span v-if="p.featured || p.product_type === 'season_pass'" class="rec-tag">推荐</span>
            </div>
            <p class="desc">{{ p.description }}</p>
            <div class="price">¥{{ (p.price_fen / 100).toFixed(2) }}</div>
            <div class="grant" v-if="p.coins_grant && p.product_type !== 'season_pass'">+{{ p.coins_grant }} 球迷币</div>
            <EntitlementPreview
              v-if="p.product_type === 'season_pass' || p.product_type === 'cosmetic'"
              :avatar-frame="cosmeticPreviewFromProduct(p).avatarFrame"
              :theme-key="cosmeticPreviewFromProduct(p).themeKey"
              :grants="buildProductGrantPreview(p)"
              :nickname="authState.user?.nickname"
              compact
            />
            <el-button type="primary" :disabled="cashBuyDisabled" @click="requestBuy(p)">
              {{ cashBuyLabel }}
            </el-button>
          </div>
        </div>
        <p v-if="isDev" class="tip">开发环境为模拟支付，购买后将进入支付结果页确认到账</p>
      </el-tab-pane>

      <el-tab-pane label="积分兑换" name="redeem">
        <el-alert
          v-if="redeemRules"
          :title="`${redeemRules.economy.redeem_points_label}：${redeemRules.economy.redeem_points_desc}`"
          type="info"
          show-icon
          :closable="false"
          class="redeem-hint"
        />
        <p v-if="redeemRules" class="economy-note">{{ redeemRules.economy.season_points_desc }}</p>

        <div v-loading="loadingRedeem" class="products">
          <div
            v-for="p in sortedRedeemProducts"
            :key="p.id"
            class="product glass-panel redeem"
            :class="{ 'sold-out': p.is_out_of_stock, affordable: isAffordable(p) }"
          >
            <div class="product-badges">
              <span v-if="p.featured" class="badge-stock featured">推荐</span>
              <span v-if="p.is_out_of_stock" class="badge-stock out">已兑完</span>
              <span v-else-if="!p.is_unlimited_stock && p.stock_remaining != null" class="badge-stock">
                全服剩 {{ p.stock_remaining }}
              </span>
              <span v-else class="badge-stock unlimited">不限量</span>
            </div>

            <h3>{{ p.name }}</h3>
            <p class="desc">{{ p.description }}</p>
            <div class="price redeem-price">{{ p.redeem_price }} 可用积分</div>

            <div v-if="authState.user && p.redeem_price" class="points-progress">
              <el-progress
                :percentage="redeemProgressPct(p)"
                :stroke-width="6"
                :color="isAffordable(p) ? '#67c23a' : 'var(--wc-accent-rose)'"
              />
              <span class="progress-label">{{ redeemProgressLabel(p) }}</span>
            </div>

            <p v-if="p.per_user_limit" class="limit-tag">
              每人限兑 {{ p.per_user_limit }} 次
              <span v-if="(p.user_purchased_count ?? 0) > 0"> · 已兑 {{ p.user_purchased_count }} 次</span>
            </p>

            <p class="grant-desc">{{ grantSummary(p) }}</p>

            <el-button type="primary" :disabled="redeemDisabled(p)" @click="confirmRedeem(p)">
              {{ redeemButtonLabel(p) }}
            </el-button>
          </div>

          <el-empty v-if="!loadingRedeem && !sortedRedeemProducts.length">
            <template #description>
              <p>{{ isDev ? '暂无兑换商品，可通过管理 API 上架' : '暂无兑换商品，敬请期待' }}</p>
            </template>
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>

    <PurchaseConfirmDialog
      v-model="purchaseDialogOpen"
      :product="pendingProduct"
      @confirm="onPurchaseConfirmed"
    />

    <PayProcessingOverlay
      :visible="payProcessing"
      :message="payProcessingMessage"
      :hint="payProcessingHint"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authState, fetchMe } from '../stores/authStore'
import {
  createOrder,
  getProducts,
  getRedeemProducts,
  getRedeemRules,
  redeemPurchase,
  fetchPaidPendingOrder,
  type Product,
  type RedeemProduct,
  type RedeemShopRules,
} from '../api/commerce'
import { showApiError } from '../utils/errorHandler'
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({
  title: '球迷商城 — 虚拟道具 | 最后一舞',
  description: '购买球迷币、赛季通行证与虚拟装扮。虚拟物品不可提现。',
  path: '/shop',
})

import PurchaseConfirmDialog from '../components/PurchaseConfirmDialog.vue'
import PayProcessingOverlay from '../components/PayProcessingOverlay.vue'
import EntitlementPreview from '../components/EntitlementPreview.vue'
import { buildProductGrantPreview, cosmeticPreviewFromProduct } from '../utils/entitlements'
import {
  isWeChatBrowser,
  clearPendingOrder,
  PENDING_ORDER_KEY,
  resolvePayChannel,
  WECHAT_PAY_HINT,
} from '../utils/payEnv'
import { useStadiumStore } from '../stores/stadiumStore'

const AGE_AGREED_KEY = 'wc_shop_age_agreed'

const cashProducts = ref<Product[]>([])
const redeemProducts = ref<RedeemProduct[]>([])
const redeemRules = ref<RedeemShopRules | null>(null)
const loadingCash = ref(false)
const loadingRedeem = ref(false)
const ageAgreed = ref(sessionStorage.getItem(AGE_AGREED_KEY) === '1')
const isDev = !import.meta.env.PROD
const route = useRoute()
const router = useRouter()
const activeTab = ref((route.query.tab as string) === 'redeem' ? 'redeem' : 'cash')

const purchaseDialogOpen = ref(false)
const pendingProduct = ref<Product | null>(null)
const payProcessing = ref(false)
const payProcessingMessage = ref('正在创建订单…')
const payProcessingHint = ref('')
const { setUiOverlay } = useStadiumStore()

const cashBuyDisabled = computed(() => !authState.user)
const cashBuyLabel = computed(() => {
  if (!authState.user) return '登录后购买'
  return '购买'
})

watch(purchaseDialogOpen, (open) => setUiOverlay('shop-purchase', open))
watch(payProcessing, (open) => setUiOverlay('shop-pay-processing', open))

const sortedRedeemProducts = computed(() => {
  const pts = authState.user?.redeem_points ?? 0
  return [...redeemProducts.value].sort((a, b) => {
    const af = a.featured ? 1 : 0
    const bf = b.featured ? 1 : 0
    if (af !== bf) return bf - af
    const aOk = (a.redeem_price ?? 0) <= pts && a.can_purchase ? 1 : 0
    const bOk = (b.redeem_price ?? 0) <= pts && b.can_purchase ? 1 : 0
    if (aOk !== bOk) return bOk - aOk
    return (a.redeem_price ?? 0) - (b.redeem_price ?? 0)
  })
})

function grantSummary(p: RedeemProduct) {
  const g = p.grant_payload
  if (!g) return '虚拟权益'
  const parts: string[] = []
  if (g.avatar_frame) parts.push('专属头像框')
  if (g.theme_key) parts.push('主题色')
  if (g.extra_free_predict_daily) parts.push(`每日免费竞猜 +${g.extra_free_predict_daily}`)
  if (g.badge_title) parts.push(`徽章「${g.badge_title}」`)
  return parts.join(' · ') || '虚拟权益'
}

function isAffordable(p: RedeemProduct) {
  const pts = authState.user?.redeem_points ?? 0
  return (p.redeem_price ?? 0) <= pts && p.can_purchase === true
}

function redeemProgressPct(p: RedeemProduct) {
  const need = p.redeem_price ?? 0
  if (need <= 0) return 100
  const have = authState.user?.redeem_points ?? 0
  return Math.min(100, Math.round((have / need) * 100))
}

function redeemProgressLabel(p: RedeemProduct) {
  const need = p.redeem_price ?? 0
  const have = authState.user?.redeem_points ?? 0
  if (have >= need) return '积分已够，可兑换'
  return `还差 ${need - have} 分`
}

function redeemButtonLabel(p: RedeemProduct) {
  if (!authState.user) return '登录后兑换'
  if (p.purchase_blocked_reason === 'out_of_stock') return '已兑完'
  if (p.purchase_blocked_reason === 'limit_reached') return '已兑换'
  if (p.purchase_blocked_reason === 'insufficient_points') return '积分不足'
  return '兑换'
}

function stockHint(p: RedeemProduct) {
  if (p.is_unlimited_stock) return '全服不限量'
  if (p.is_out_of_stock) return '全服已兑完'
  return `全服剩余 ${p.stock_remaining ?? 0} / ${p.stock_total ?? 0}`
}

async function confirmRedeem(p: RedeemProduct) {
  if (!authState.user) {
    router.push('/login')
    return
  }
  if (redeemDisabled(p)) return
  try {
    await ElMessageBox.confirm(
      `确认消耗 ${p.redeem_price} 可用积分兑换「${p.name}」？\n${stockHint(p)}\n获得：${grantSummary(p)}`,
      '确认兑换',
      { confirmButtonText: '确认兑换', cancelButtonText: '取消', type: 'info' },
    )
    await redeem(p)
  } catch {
    /* cancelled */
  }
}

function redeemDisabled(p: RedeemProduct) {
  if (!authState.user) return true
  return !p.can_purchase
}

async function loadCash() {
  loadingCash.value = true
  try {
    cashProducts.value = await getProducts()
  } catch (e) {
    showApiError(e)
  } finally {
    loadingCash.value = false
  }
}

async function loadRedeem() {
  loadingRedeem.value = true
  try {
    const [products, rules] = await Promise.all([getRedeemProducts(), getRedeemRules()])
    redeemProducts.value = products
    redeemRules.value = rules
  } catch (e) {
    showApiError(e)
  } finally {
    loadingRedeem.value = false
  }
}

async function syncPendingPayment(): Promise<boolean> {
  if (!authState.accessToken) return false
  const pendingNo = sessionStorage.getItem(PENDING_ORDER_KEY)
  if (!pendingNo) return false

  const paid = await fetchPaidPendingOrder()
  if (paid) {
    clearPendingOrder()
    await fetchMe()
    await router.replace({ path: '/shop/result', query: { out_trade_no: paid.out_trade_no } })
    return true
  }

  // 刚从支付宝回来、notify 尚未到达：进结果页轮询，不要停在商城
  await router.replace({ path: '/shop/result', query: { out_trade_no: pendingNo } })
  return true
}

async function load() {
  if (authState.accessToken) {
    const redirected = await syncPendingPayment()
    if (redirected) return
    await fetchMe()
  }
  await Promise.all([loadCash(), loadRedeem()])
}

function requestBuy(product: Product) {
  if (!authState.user) {
    router.push('/login')
    return
  }
  if (ageAgreed.value) {
    void executeBuy(product.id)
    return
  }
  pendingProduct.value = product
  purchaseDialogOpen.value = true
}

function onPurchaseConfirmed() {
  if (!pendingProduct.value) return
  ageAgreed.value = true
  sessionStorage.setItem(AGE_AGREED_KEY, '1')
  void executeBuy(pendingProduct.value.id)
  pendingProduct.value = null
}

async function executeBuy(productId: number) {
  if (payProcessing.value) return
  if (isWeChatBrowser()) {
    await ElMessageBox.alert(WECHAT_PAY_HINT, '请用浏览器打开', {
      confirmButtonText: '我知道了',
      type: 'warning',
    })
    return
  }
  payProcessing.value = true
  payProcessingMessage.value = '正在创建订单…'
  payProcessingHint.value = ''
  try {
    const payChannel = resolvePayChannel()
    const { order, pay_url } = await createOrder(productId, ageAgreed.value, payChannel)
    const isMock = pay_url.includes('mock=1')

    if (isMock) {
      if (!isDev) {
        ElMessage.error('生产环境不支持模拟支付')
        return
      }
      payProcessingMessage.value = '正在前往支付结果…'
      payProcessingHint.value = '模拟支付宝回跳，请稍候'
      await router.push({
        path: '/shop/result',
        query: { mock: '1', out_trade_no: order.out_trade_no },
      })
      return
    }

    payProcessingMessage.value = '正在跳转支付宝…'
    payProcessingHint.value =
      payChannel === 'wap' ? '请在支付宝页面完成支付（可唤起支付宝 App）' : '请在支付宝页面完成支付'
    sessionStorage.setItem(PENDING_ORDER_KEY, order.out_trade_no)
    window.location.href = pay_url
  } catch (e) {
    showApiError(e)
  } finally {
    payProcessing.value = false
  }
}

async function redeem(p: RedeemProduct) {
  try {
    const res = await redeemPurchase(p.id)
    await fetchMe()
    await loadRedeem()
    const stockMsg = res.stock_remaining != null ? ` · 全服剩余 ${res.stock_remaining}` : ''
    ElMessage.success(`兑换成功！已获得 ${grantSummary(p)} · 剩余 ${res.redeem_points_after} 可用积分${stockMsg}`)
  } catch (e) {
    showApiError(e)
  }
}

watch(activeTab, (tab) => {
  if (tab === 'redeem' && !redeemProducts.value.length) loadRedeem()
})

onMounted(load)
</script>

<style scoped>
.shop {
  max-width: 960px;
  margin: 0 auto;
  background: transparent;
}

@media (min-width: 769px) {
  .shop {
    padding: 16px 20px 32px;
  }
}
.header {
  padding: 20px;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
}
.balances {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 8px;
  font-size: 0.9rem;
}
.balances .redeem {
  color: var(--wc-accent-rose);
}
.shop-tabs {
  margin-top: 8px;
}
.age-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  margin-top: 8px;
  border: 1px solid rgba(212, 165, 116, 0.2);
  background: rgba(14, 16, 32, 0.72);
}
.age-notice-badge {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 900;
  color: #1a1208;
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
}
.age-notice-body strong {
  display: block;
  font-size: 0.9rem;
  color: var(--wc-accent-gold);
  margin-bottom: 4px;
}
.age-notice-body p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  line-height: 1.55;
}
.products {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.product {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.product.redeem.affordable {
  border-color: rgba(103, 194, 58, 0.35);
}
.product-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.product h3 {
  margin: 0;
}

.rec-tag {
  flex-shrink: 0;
  font-size: 0.68rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(212, 165, 116, 0.2);
  color: var(--wc-accent-gold);
  font-weight: 700;
}

.product.featured {
  border-color: rgba(212, 165, 116, 0.45);
}
.desc {
  color: var(--wc-text-muted);
  font-size: 0.85rem;
  flex: 1;
}
.price {
  font-size: 1.3rem;
  color: var(--wc-accent-gold);
  font-weight: 700;
}
.redeem-price {
  color: var(--wc-accent-rose);
}
.grant {
  font-size: 0.85rem;
  color: var(--wc-accent-rose);
}
.grant-desc {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  margin: 0;
}
.limit-tag {
  font-size: 0.75rem;
  color: var(--wc-accent-gold);
  margin: 0;
}
.points-progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.progress-label {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.benefits {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}
.tip {
  margin-top: 20px;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  text-align: center;
}
.redeem-hint {
  margin-bottom: 12px;
}
.product.redeem.sold-out {
  opacity: 0.72;
}
.product-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 4px;
}
.badge-stock {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold);
}
.badge-stock.featured {
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
}
.badge-stock.out {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}
.badge-stock.unlimited {
  color: var(--wc-text-muted);
  background: rgba(255, 255, 255, 0.06);
}
.economy-note {
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  margin: 0 0 12px;
}

@media (max-width: 768px) {
  .shop {
    max-width: 100%;
  }
  .header {
    padding: 14px 16px;
  }
  .balances {
    flex-direction: column;
    gap: 8px;
  }
  .age-notice {
    flex-direction: row;
    padding: 12px;
  }
  .product .el-button {
    width: 100%;
    min-height: 44px;
  }
}

@media (max-width: 480px) {
  .products {
    grid-template-columns: 1fr;
  }
}
</style>
