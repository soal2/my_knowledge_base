import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/files': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    }
  }
})
