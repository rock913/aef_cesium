import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'

export default defineConfig({
  plugins: [vue(), cesium()],
  server: {
    port: 8504,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8505',
        changeOrigin: true
      },
      '/health': {
        target: 'http://127.0.0.1:8505',
        changeOrigin: true
      }
    }
  }
})
