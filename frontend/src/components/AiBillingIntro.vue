<template>
  <div v-if="visible" class="billing-intro glass-inner">
    <div class="intro-head">
      <span class="intro-icon">🤖</span>
      <div>
        <h3>AI 分析使用说明</h3>
        <p>首次使用前请了解计费与免责规则，确认后不再重复弹出</p>
      </div>
    </div>
    <ul class="intro-list">
      <li><strong>娱乐参考</strong> — 分析结果不保证准确，不构成投注建议</li>
      <li><strong>免费额度</strong> — 登录用户每日有免费次数，赛前/赛中模式分别计费</li>
      <li><strong>缓存免扣</strong> — 相同对阵近期分析过则直接读缓存，不扣球迷币</li>
      <li><strong>强制刷新</strong> — 勾选后将忽略缓存并额外扣币，请按需使用</li>
    </ul>
    <div class="intro-actions">
      <router-link to="/legal/ai" class="link">查看完整 AI 使用说明 →</router-link>
      <button type="button" class="ack-btn" @click="$emit('ack')">我知道了，继续分析</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ visible: boolean }>()
defineEmits<{ ack: [] }>()
</script>

<style scoped>
.billing-intro {
  margin: 14px 0 4px;
  padding: 16px 18px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.08);
}

.intro-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.intro-icon {
  font-size: 1.6rem;
  line-height: 1;
}

.intro-head h3 {
  margin: 0 0 4px;
  font-size: 1rem;
  color: #f0d9b5;
}

.intro-head p {
  margin: 0;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.65);
}

.intro-list {
  margin: 0 0 14px;
  padding-left: 18px;
  font-size: 0.84rem;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.55;
}

.intro-list strong {
  color: var(--wc-accent-gold);
}

.intro-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.link {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
}

.link:hover {
  color: var(--wc-accent-gold);
}

.ack-btn {
  padding: 8px 18px;
  border: none;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 700;
  color: #1a1208;
  cursor: pointer;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 100%);
  box-shadow: 0 2px 12px rgba(212, 165, 116, 0.35);
}

.ack-btn:hover {
  filter: brightness(1.05);
}
</style>
