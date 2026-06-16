import { ref } from 'vue'
import type { PredictSharePayload } from '../components/PredictShareSheet.vue'

type SheetApi = { show: (payload: PredictSharePayload) => void }

const sheetApi = ref<SheetApi | null>(null)

export function registerPredictShareSheet(api: SheetApi | null) {
  sheetApi.value = api
}

export function openPredictShareSheet(payload: PredictSharePayload) {
  sheetApi.value?.show(payload)
}
