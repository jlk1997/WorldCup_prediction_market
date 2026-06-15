import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'

const SITE_META = {
  title: '最后一舞：世界杯2026',
  description: '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。',
}

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const siteUrl = (env.VITE_SITE_URL || 'https://loveaibaby.cn').replace(/\/$/, '')
  const verificationTags: string[] = []
  if (env.VITE_GOOGLE_SITE_VERIFICATION) {
    verificationTags.push(
      `<meta name="google-site-verification" content="${env.VITE_GOOGLE_SITE_VERIFICATION}" />`,
    )
  }
  if (env.VITE_BAIDU_SITE_VERIFICATION) {
    verificationTags.push(
      `<meta name="baidu-site-verification" content="${env.VITE_BAIDU_SITE_VERIFICATION}" />`,
    )
  }
  const verificationHtml = verificationTags.length ? verificationTags.join('\n    ') : ''

  return {
    plugins: [
      vue(),
      AutoImport({
        resolvers: [ElementPlusResolver({ importStyle: 'css' })],
        dts: command === 'serve' ? 'src/auto-imports.d.ts' : false,
      }),
      Components({
        resolvers: [ElementPlusResolver({ importStyle: 'css' })],
        dts: command === 'serve' ? 'src/components.d.ts' : false,
      }),
      {
        name: 'html-site-meta',
        transformIndexHtml(html) {
          return html
            .replaceAll('__SITE_URL__', siteUrl)
            .replaceAll('__SITE_TITLE__', SITE_META.title)
            .replaceAll('__SITE_DESCRIPTION__', SITE_META.description)
            .replaceAll('__SITE_VERIFICATION_TAGS__', verificationHtml)
        },
      },
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/element-plus')) {
              return 'element-plus'
            }
            if (id.includes('node_modules/@element-plus/icons-vue')) {
              return 'element-plus-icons'
            }
            if (id.includes('node_modules/vue-router') || id.includes('node_modules/vue/')) {
              return 'vue-vendor'
            }
          },
        },
      },
      chunkSizeWarningLimit: 600,
    },
    server: {
      port: 10087,
      host: '0.0.0.0',
    },
  }
})
