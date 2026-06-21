import { ref } from 'vue'
import type { CollectibleSharePayload } from '../components/CollectibleShareSheet.vue'

type SheetApi = { show: (payload: CollectibleSharePayload) => void }

const sheetApi = ref<SheetApi | null>(null)

export function registerCollectibleShareSheet(api: SheetApi | null) {
  sheetApi.value = api
}

export function openCollectibleShare(payload: CollectibleSharePayload) {
  sheetApi.value?.show(payload)
}
