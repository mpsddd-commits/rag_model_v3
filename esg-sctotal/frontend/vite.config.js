import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
/* [이슈] Tailwind CSS v4 vite 플러그인 추가 — 누락 시 모든 Tailwind 클래스 미적용 */
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'url'

// https://vite.dev/config/
export default defineConfig({
  /* [이슈] tailwindcss() 플러그인 추가 */
  plugins: [react(), tailwindcss()],
  base: "/",
  server: {
    host: '0.0.0.0',
    port: 80,
    allowedHosts: ['localhost', 'weareithero.cloud'],
    proxy: {
      '/api': {
        // target: 'http://main.weareithero.cloud',
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        headers: {
          // 'Origin': 'http://main.weareithero.cloud'
          'Origin': 'http://localhost:8000'
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@errors': fileURLToPath(new URL('./src/homes/errors', import.meta.url)),
      '@components': fileURLToPath(new URL('./src/components', import.meta.url)),
      '@styles': fileURLToPath(new URL('./src/styles', import.meta.url)),
      '@gates': fileURLToPath(new URL('./src/homes/gates', import.meta.url)),
      '@logins': fileURLToPath(new URL('./src/homes/logins', import.meta.url)),
      '@mains': fileURLToPath(new URL('./src/homes/mains', import.meta.url)),
      '@assets': fileURLToPath(new URL('./src/assets', import.meta.url)),
      '@hooks': fileURLToPath(new URL('./src/hooks', import.meta.url)),
      '@utils': fileURLToPath(new URL('./src/utils', import.meta.url)),
      '@admin': fileURLToPath(new URL('./src/homes/admin', import.meta.url)),
      '@partners': fileURLToPath(new URL('./src/homes/partners', import.meta.url)),
    }
  },
})
