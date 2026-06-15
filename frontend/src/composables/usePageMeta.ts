import { onUnmounted } from 'vue'
import { useHead } from '@unhead/vue'
import { clearJsonLd } from '../utils/jsonLd'

const SITE_NAME = '最后一舞'
const DEFAULT_DESCRIPTION =
  '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。'

function siteUrl() {
  return (import.meta.env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')
}

export type PageMetaInput = {
  title?: string
  description?: string
  path?: string
  ogImage?: string
  noIndex?: boolean
}

export function usePageMeta(input: PageMetaInput | (() => PageMetaInput)) {
  const resolve = () => (typeof input === 'function' ? input() : input)

  useHead(() => {
    const meta = resolve()
    const title = meta.title || `${SITE_NAME}：世界杯2026`
    const description = meta.description || DEFAULT_DESCRIPTION
    const url = meta.path ? `${siteUrl()}${meta.path.startsWith('/') ? meta.path : `/${meta.path}`}` : `${siteUrl()}/`
    const image = meta.ogImage || `${siteUrl()}/share-og.png`

    return {
      title,
      meta: [
        { name: 'description', content: description },
        ...(meta.noIndex ? [{ name: 'robots', content: 'noindex, nofollow' }] : []),
        { property: 'og:type', content: 'website' },
        { property: 'og:site_name', content: SITE_NAME },
        { property: 'og:title', content: title },
        { property: 'og:description', content: description },
        { property: 'og:url', content: url },
        { property: 'og:image', content: image },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: title },
        { name: 'twitter:description', content: description },
        { name: 'twitter:image', content: image },
      ],
      link: [{ rel: 'canonical', href: url }],
    }
  })

  onUnmounted(() => {
    clearJsonLd()
  })
}

export function useRoutePageMeta(
  metaRef: () => PageMetaInput,
) {
  useHead(() => {
    const meta = metaRef()
    const title = meta.title || `${SITE_NAME}：世界杯2026`
    const description = meta.description || DEFAULT_DESCRIPTION
    const url = meta.path ? `${siteUrl()}${meta.path.startsWith('/') ? meta.path : `/${meta.path}`}` : `${siteUrl()}/`
    const image = meta.ogImage || `${siteUrl()}/share-og.png`
    return {
      title,
      meta: [
        { name: 'description', content: description },
        { property: 'og:title', content: title },
        { property: 'og:description', content: description },
        { property: 'og:url', content: url },
        { property: 'og:image', content: image },
      ],
      link: [{ rel: 'canonical', href: url }],
    }
  })
}
