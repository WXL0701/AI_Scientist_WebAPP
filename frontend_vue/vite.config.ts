import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8081',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/auth': 'http://localhost:8081',
      '/runs': {
        target: 'http://localhost:8081',
        changeOrigin: true,
        bypass: (req: any) => {
          const accept = req.headers.accept || ''
          const mode = req.headers['sec-fetch-mode']
          // If browser is navigating, serve index.html
          if (mode === 'navigate') {
            return req.url
          }
          // If it asks for HTML and NOT JSON, serve index.html
          if (accept.includes('text/html') && !accept.includes('application/json')) {
            return req.url
          }
        }
      },
      '/promptsets': 'http://localhost:8081',
      '/health': 'http://localhost:8081'
    }
  }
})
