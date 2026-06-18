<template>
  <CardRevealDialog
    v-model="collectibleRevealState.visible"
    :drop="collectibleRevealState.drop"
    :subtitle-override="collectibleRevealState.subtitle"
    @closed="closeCollectibleReveal"
  />
</template>

<script setup lang="ts">
import CardRevealDialog from '@/components/collectible/CardRevealDialog.vue'
import {
  collectibleRevealState,
  closeCollectibleReveal,
} from '@/stores/collectibleRevealStore'
</script>
