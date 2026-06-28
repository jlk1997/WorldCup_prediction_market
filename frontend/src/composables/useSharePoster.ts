import { ref } from 'vue'

export interface SharePosterPayload {
  variant?: 'ai' | 'chain'
  title: string
  subtitle: string
  extra?: string
}

type SheetApi = { show: (payload: SharePosterPayload) => void }

const sheetApi = ref<SheetApi | null>(null)

export function registerSharePosterSheet(api: SheetApi | null) {
  sheetApi.value = api
}

export function openSharePoster(payload: SharePosterPayload) {
  sheetApi.value?.show(payload)
}
