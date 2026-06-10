<template>
  <el-dialog
    v-model="visible"
    :show-close="true"
    :close-on-click-modal="false"
    :width="isMobile ? 'min(420px, 92vw)' : '440px'"
    class="purchase-confirm-dialog"
    align-center
    append-to-body
    destroy-on-close
    @closed="onClosed"
  >
    <template #header>
      <div class="dialog-head">
        <span class="age-badge">18+</span>
        <div>
          <h3 class="dialog-title">虚拟商品购买确认</h3>
          <p class="dialog-sub">请阅读并确认以下条款后继续支付</p>
        </div>
      </div>
    </template>

    <div v-if="product" class="product-summary glass-inner">
      <div class="summary-row">
        <span class="label">商品</span>
        <strong>{{ product.name }}</strong>
      </div>
      <div class="summary-row">
        <span class="label">支付金额</span>
        <strong class="price">¥{{ (product.price_fen / 100).toFixed(2) }}</strong>
      </div>
      <div v-if="product.coins_grant" class="summary-row">
        <span class="label">到账</span>
        <strong class="grant">+{{ product.coins_grant }} 球迷币</strong>
      </div>
      <div v-if="product.grant_season_pass_days" class="summary-row">
        <span class="label">权益</span>
        <strong>赛季通行证 {{ product.grant_season_pass_days }} 天</strong>
      </div>
    </div>

    <EntitlementPreview
      v-if="product && showPreview"
      class="preview-block"
      :avatar-frame="previewFrame"
      :theme-key="previewTheme"
      :grants="grantLines"
      :nickname="authState.user?.nickname"
      compact
    />

    <ul class="rule-list">
      <li>本人已满 <strong>18 周岁</strong>，具备完全民事行为能力</li>
      <li>球迷币、通行证等为<strong>虚拟道具</strong>，仅限站内消费使用</li>
      <li>购买成功后<strong>不可退款、不可提现</strong>，请谨慎确认金额</li>
    </ul>

    <label class="agree-row" :class="{ checked: agreed }">
      <el-checkbox v-model="agreed" />
      <span>我已阅读并同意上述说明，确认继续购买</span>
    </label>

    <template #footer>
      <div class="dialog-footer">
        <el-button class="footer-btn" @click="visible = false">取消</el-button>
        <el-button type="primary" class="footer-btn footer-btn--primary" :disabled="!agreed" @click="confirm">
          同意并继续支付
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Product } from '../api/commerce'
import { authState } from '../stores/authStore'
import { useBreakpoint } from '../composables/useBreakpoint'
import EntitlementPreview from './EntitlementPreview.vue'
import { buildProductGrantPreview, cosmeticPreviewFromProduct } from '../utils/entitlements'

const visible = defineModel<boolean>({ default: false })

const props = defineProps<{
  product: Product | null
}>()

const emit = defineEmits<{ confirm: [] }>()

const { isMobile } = useBreakpoint()
const agreed = ref(false)

const showPreview = computed(
  () => props.product?.product_type === 'season_pass' || props.product?.product_type === 'cosmetic',
)
const grantLines = computed(() => (props.product ? buildProductGrantPreview(props.product) : []))
const previewFrame = computed(() => cosmeticPreviewFromProduct(props.product).avatarFrame)
const previewTheme = computed(() => cosmeticPreviewFromProduct(props.product).themeKey)

watch(visible, (open) => {
  if (open) agreed.value = false
})

function confirm() {
  if (!agreed.value) return
  visible.value = false
  emit('confirm')
}

function onClosed() {
  agreed.value = false
}
</script>

<style scoped>
.dialog-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-right: 24px;
}

.age-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 900;
  color: #1a1208;
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
  box-shadow: 0 0 12px rgba(212, 165, 116, 0.35);
}

.dialog-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: #f5f0e8;
  line-height: 1.3;
}

.dialog-sub {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
}

.product-summary {
  padding: 12px 14px;
  border-radius: 10px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 0.88rem;
}

.summary-row .label {
  color: var(--wc-text-muted);
  flex-shrink: 0;
}

.summary-row strong {
  color: #f5f0e8;
  text-align: right;
}

.summary-row .price {
  font-size: 1.15rem;
  color: var(--wc-accent-gold);
}

.summary-row .grant {
  color: var(--wc-accent-rose);
}

.rule-list {
  margin: 0 0 14px;
  padding-left: 1.15rem;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.65;
}

.rule-list strong {
  color: var(--wc-accent-gold);
  font-weight: 700;
}

.agree-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.22);
  background: rgba(212, 165, 116, 0.06);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.agree-row.checked {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.12);
}

.agree-row span {
  font-size: 0.85rem;
  color: #f0e6d8;
  line-height: 1.45;
  padding-top: 1px;
}

.dialog-footer {
  display: flex;
  gap: 10px;
  width: 100%;
}

.footer-btn {
  flex: 1;
  min-height: 44px;
  margin: 0 !important;
}

.footer-btn--primary:disabled {
  opacity: 0.55;
}

@media (max-width: 768px) {
  .dialog-footer {
    flex-direction: column-reverse;
  }
}
</style>

<style>
.purchase-confirm-dialog.el-dialog {
  background: rgba(14, 16, 32, 0.98) !important;
  border: 1px solid rgba(212, 165, 116, 0.28);
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
  padding: 0;
  overflow: hidden;
}

.purchase-confirm-dialog .el-dialog__header {
  padding: 18px 20px 12px;
  margin: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.purchase-confirm-dialog .el-dialog__body {
  padding: 16px 20px 8px;
  color: var(--wc-text-secondary);
}

.purchase-confirm-dialog .el-dialog__footer {
  padding: 12px 20px calc(16px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.purchase-confirm-dialog .el-dialog__headerbtn {
  top: 14px;
  right: 14px;
  width: 32px;
  height: 32px;
}

.purchase-confirm-dialog .el-dialog__headerbtn .el-dialog__close {
  color: var(--wc-text-muted);
}

.purchase-confirm-dialog .el-checkbox__label {
  display: none;
}

@media (max-width: 768px) {
  .purchase-confirm-dialog.el-dialog {
    width: min(420px, 92vw) !important;
    max-width: 92vw !important;
    margin: 12px auto !important;
  }
}
</style>
