<template>
  <Teleport to="body">
    <div v-if="visible" class="pay-processing-overlay" role="status" aria-live="polite">
      <div class="pay-processing-card glass-panel">
        <div class="spinner" aria-hidden="true" />
        <p class="message">{{ message }}</p>
        <p v-if="hint" class="hint">{{ hint }}</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean
  message: string
  hint?: string
}>()
</script>

<style scoped>
.pay-processing-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(4, 6, 14, 0.72);
  backdrop-filter: blur(6px);
}

.pay-processing-card {
  width: min(360px, 92vw);
  padding: 28px 24px;
  text-align: center;
  border: 1px solid rgba(212, 165, 116, 0.28);
}

.spinner {
  width: 44px;
  height: 44px;
  margin: 0 auto 16px;
  border: 3px solid rgba(212, 165, 116, 0.2);
  border-top-color: var(--wc-accent-gold);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.message {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #f5f0e8;
}

.hint {
  margin: 8px 0 0;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
