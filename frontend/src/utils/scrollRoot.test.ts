/**
 * Unit tests for scrollRoot helpers.
 */
import { afterEach, describe, expect, it } from 'vitest'
import {
  cleanupElementScrollLock,
  getScrollRoot,
  scrollElementIntoRootView,
  waitForElement,
} from './scrollRoot'

describe('scrollRoot module', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    document.body.className = ''
    document.body.removeAttribute('style')
  })

  it('exports scroll helpers', () => {
    expect(typeof getScrollRoot).toBe('function')
    expect(typeof scrollElementIntoRootView).toBe('function')
    expect(typeof waitForElement).toBe('function')
    expect(typeof cleanupElementScrollLock).toBe('function')
  })

  it('getScrollRoot prefers .main-content ancestor', () => {
    document.body.innerHTML = `
      <main class="el-main main-content" style="height:400px;overflow:auto">
        <div id="card">card</div>
      </main>
    `
    const card = document.getElementById('card')!
    expect(getScrollRoot(card)).toBe(document.querySelector('.main-content'))
  })

  it('cleanupElementScrollLock removes EP body lock class', () => {
    document.body.classList.add('el-popup-parent--hidden')
    document.body.style.overflow = 'hidden'
    cleanupElementScrollLock()
    expect(document.body.classList.contains('el-popup-parent--hidden')).toBe(false)
    expect(document.body.style.overflow).toBe('')
  })
})
