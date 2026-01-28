import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/auth': 'http://localhost:8080',
      '/runs': 'http://localhost:8080',
      '/promptsets': 'http://localhost:8080',
      '/health': 'http://localhost:8080'
    }
  }
})
