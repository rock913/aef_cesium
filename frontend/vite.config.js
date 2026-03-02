import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'
import http from 'node:http'

const keepAliveAgent = new http.Agent({
  keepAlive: true,
  maxSockets: 256
})

// Used for one-shot retry on transient socket resets (e.g. backend restart while
// the dev server keeps an idle keep-alive connection).
const freshAgent = new http.Agent({
  keepAlive: false,
  maxSockets: 256
})

function attachProxyDebug(proxy, opts) {
  const target = opts?.target || ''
  try {
    proxy.on('error', (err, req, res) => {
      const code = err?.code || ''
      const msg = err?.message || String(err)
      const url = req?.url || ''
      const method = req?.method || ''

      // Mitigation: if the backend restarted, the proxy may attempt to reuse an
      // idle keep-alive socket and get ECONNRESET. For idempotent tile GETs,
      // retry once with a fresh (non-keepalive) agent.
      const isTileGet = method === 'GET' && typeof url === 'string' && url.startsWith('/api/tiles/')
      const canRetry = isTileGet && (code === 'ECONNRESET' || code === 'EPIPE')
      if (canRetry && req && !req.__oneearth_proxy_retried) {
        req.__oneearth_proxy_retried = true
        try {
          proxy.web(req, res, { target, agent: freshAgent })
          return
        } catch (_) {
          // fall through
        }
      }

      console.error(`[proxy:error] ${method} ${url} -> ${target} ${code} ${msg}`)

      // Avoid leaving the client hanging with a reset socket.
      try {
        if (res && !res.headersSent) {
          res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
        }
        res?.end?.(JSON.stringify({
          error: 'proxy_error',
          code,
          message: msg,
          target,
          url,
          hint: 'Backend may be restarting; retry shortly.'
        }))
      } catch (_) {
        // ignore
      }
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

const apiHost = process.env.API_HOST || '127.0.0.1'
const apiPort = process.env.API_PORT || '8405'
const apiTarget = `http://${apiHost}:${apiPort}`

const frontendPort = process.env.FRONTEND_PORT ? Number(process.env.FRONTEND_PORT) : 8404

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
    port: frontendPort,
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
        target: apiTarget,
        changeOrigin: true,
        agent: keepAliveAgent,
        timeout: 30000,
        proxyTimeout: 30000,
        configure: (proxy, options) => attachProxyDebug(proxy, options)
      },
      '/health': {
        target: apiTarget,
        changeOrigin: true,
        agent: keepAliveAgent,
        timeout: 5000,
        proxyTimeout: 5000,
        configure: (proxy, options) => attachProxyDebug(proxy, options)
      }
    }
  }
})
