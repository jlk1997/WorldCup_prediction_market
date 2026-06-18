import { nextTick, type Ref } from 'vue'

/** Scroll predict hall so highlighted match card is visible (page-level scroll). */
export function usePredictHighlightScroll(
  highlightId: Ref<number | null>,
  scrollToIndex?: Ref<number | null>,
) {
  async function scrollToHighlight() {
    const id = highlightId.value
    if (!id) return
    await nextTick()
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

    const card = document.querySelector(`[data-match-id="${id}"]`) as HTMLElement | null
    if (!card) return

    const scrollRoot =
      (card.closest('.main-content') as HTMLElement | null) ??
      (document.scrollingElement as HTMLElement | null)

    if (scrollRoot && scrollRoot !== document.documentElement) {
      const rootRect = scrollRoot.getBoundingClientRect()
      const cardRect = card.getBoundingClientRect()
      const targetTop =
        scrollRoot.scrollTop + cardRect.top - rootRect.top - Math.max(0, (rootRect.height - cardRect.height) / 2)
      scrollRoot.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' })
      return
    }

    card.scrollIntoView({ behavior: 'smooth', block: 'center' })

    void scrollToIndex?.value
  }

  return { scrollToHighlight }
}
