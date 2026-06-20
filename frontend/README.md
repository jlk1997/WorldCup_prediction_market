# Vue 3 + TypeScript + Vite

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).

## Mobile scroll architecture

Long pages scroll through a **single vertical scroll root**: `.el-main.main-content` in `App.vue`. `html` / `body` stay `overflow: hidden`; do not add page-level `height: 100%` + `overflow-y: auto` on route views.

- Use the `mobile-page` class on page roots for bottom safe-area / fixed nav padding.
- Internal drawers (e.g. schedule drawer) may scroll inside themselves; avoid nested scroll containers on the main page tree.
- Coach / highlight scrolling should use `getScrollRoot()` from `src/utils/scrollRoot.ts`, not `window.scrollIntoView`.
- Element Plus dialogs that stack with coaches should set `:lock-scroll="false"`; the app manages scroll locking and cleans up `el-popup-parent--hidden` via `cleanupElementScrollLock()`.
- On iOS / WeChat / iPad, `--app-height` and `--app-offset-top` come from `visualViewport` (`useMobileViewport` + `utils/visualViewport.ts`) so the shell tracks browser chrome.
- Prefer `var(--app-height, 100dvh)` over raw `100vh` in layout calculations.

## Card drop reveal

- Global host: `CollectibleDropHost` in `App.vue` → `CardRevealDialog`.
- Open via `openCollectibleReveal()` from `collectibleRevealStore.ts` (predict win chains from settlement after ~2.2s, sign-in, arena rally, synthesis, header notifier).
- Settlement closes before card reveal opens (orchestrator priority); card dialog uses staged flip animation and `:lock-scroll="false"`.

## Scripts

- `npm run dev` — local dev server
- `npm run build` — production build
- `npm run test:unit` — Vitest unit tests (`src/**/*.test.ts`)

## Manual QA (iOS Safari / WeChat)

After scroll or guide changes, verify on real devices:

| Route | Checks |
|-------|--------|
| `/`, `/predict`, `/arena`, `/collection`, `/leaderboard` | Full-page scroll to bottom; content not hidden behind bottom nav |
| WeChat in-app browser | Toolbar show/hide does not break scroll; no nested inner scroll panes |
| First-login onboarding | Tour → `/predict`: spotlight shows real match cards, not dialog underlay |
| Predict win + card drop | Settlement confetti → auto card reveal (~2.2s) or tap「立即查看新卡」 |
| Card synthesis | `/collection` synthesize shows flip reveal dialog |
| Logout / switch account | No stale settlement, coach, or reward overlays |
