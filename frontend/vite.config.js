import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'
import http from 'node:http'

const keepAliveAgent = new http.Agent({
  keepAlive: true,
  maxSockets: 256
})

function attachProxyDebug(proxy, opts) {
  const target = opts?.target || ''
  try {
    proxy.on('error', (err, req) => {
      const code = err?.code || ''
      const msg = err?.message || String(err)
      const url = req?.url || ''
      const method = req?.method || ''
      console.error(`[proxy:error] ${method} ${url} -> ${target} ${code} ${msg}`)
    })
    proxy.on('proxyRes', (proxyRes, req) => {
      const status = proxyRes?.statusCode
      if (status && status >= 500) {
        const url = req?.url || ''
        const method = req?.method || ''
        console.warn(`[proxy:5xx] ${method} ${url} -> ${target} HTTP ${status}`)
      }
    })
  } catch (_) {
    // ignore
  }
}

export default defineConfig({
  plugins: [
    vue(),
    cesium({
      // Avoid common reverse-proxy path conflicts on `/cesium/*`.
      // The plugin will serve this path in dev and copy assets into `dist/__cesium/*` on build.
      cesiumBaseUrl: '__cesium/'
    })
  ],
  server: {
    port: 8504,
    host: '0.0.0.0',
    strictPort: true,
    // Optional: set these env vars when accessing via a public IP / reverse proxy
    // to prevent the Vite client from trying an unreachable websocket endpoint.
    hmr: process.env.VITE_DISABLE_HMR === '1'
      ? false
      : {
          protocol: process.env.VITE_HMR_PROTOCOL || undefined,
          host: process.env.VITE_HMR_HOST || undefined,
          port: process.env.VITE_HMR_PORT ? Number(process.env.VITE_HMR_PORT) : undefined,
          clientPort: process.env.VITE_HMR_CLIENT_PORT ? Number(process.env.VITE_HMR_CLIENT_PORT) : undefined
        },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8505',
        changeOrigin: true,
        agent: keepAliveAgent,
        timeout: 30000,
        proxyTimeout: 30000,
        configure: (proxy, options) => attachProxyDebug(proxy, options)
      },
      '/health': {
        target: 'http://127.0.0.1:8505',
        changeOrigin: true,
        agent: keepAliveAgent,
        timeout: 5000,
        proxyTimeout: 5000,
        configure: (proxy, options) => attachProxyDebug(proxy, options)
      }
    }
  }
})
