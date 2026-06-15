const SCRIPT_ID = 'wc-json-ld'

export function injectJsonLd(data: Record<string, unknown>) {
  if (typeof document === 'undefined') return
  let el = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null
  if (!el) {
    el = document.createElement('script')
    el.id = SCRIPT_ID
    el.type = 'application/ld+json'
    document.head.appendChild(el)
  }
  el.textContent = JSON.stringify(data)
}

export function clearJsonLd() {
  document.getElementById(SCRIPT_ID)?.remove()
}
