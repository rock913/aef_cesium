/**
 * API Service for communicating with backend
 */
import axios from 'axios'

// Default to same-origin so remote users don't accidentally call *their own* localhost.
// In dev, Vite proxies /api -> backend (see vite.config.js).
// Override with VITE_API_BASE (e.g. https://your-domain.com or http://47.245.113.151:8503).
const API_BASE = import.meta.env.VITE_API_BASE || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

// Normalize error messages so the UI can show actionable backend details.
api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    try {
      const status = error?.response?.status
      const data = error?.response?.data
      const detail = (data && (data.detail ?? data.error ?? data)) || null
      const detailText = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : ''
      const baseMsg = error?.message || 'Request failed'

      const msg = status
        ? `${baseMsg} (HTTP ${status})${detailText ? `: ${detailText}` : ''}`
        : baseMsg

      const e2 = new Error(msg)
      e2.status = status
      e2.detail = detail
      throw e2
    } catch (_) {
      // Fallback to original error
      throw error
    }
  }
)

export const apiService = {
  /**
   * 获取所有可用地点
   */
  async getLocations() {
    const { data } = await api.get('/api/locations')
    return data
  },

  /**
   * 获取所有 AI 模式
   */
  async getModes() {
    const { data } = await api.get('/api/modes')
    return data
  },

  /**
   * 获取 V5 Missions（任务驱动演示主线）
   */
  async getMissions() {
    const { data } = await api.get('/api/missions')
    return data
  },

  /**
   * 获取图层 Tile URL
   */
  async getLayer(mode, location) {
    const { data } = await api.get('/api/layers', {
      params: { mode, location }
    })
    return data
  },

  /**
   * 获取 Sentinel-2 真彩底图 Tile URL（用于“永不白屏”的底图兜底）
   */
  async getSentinel2Layer(location) {
    const { data } = await api.get('/api/sentinel2', {
      params: { location }
    })
    return data
  },

  /**
   * 动态统计：将 mockStats 替换为云端 reduceRegion 统计
   */
  async getStats(mode, location, options = {}) {
    const payload = {
      mode,
      location
    }
    if (options.scale_m) payload.scale_m = options.scale_m
    const { data } = await api.post('/api/stats', payload)
    return data
  },

  /**
   * 生成《区域空间监测简报》（模板/LLM）
   */
  async getReport(mission_id, stats) {
    const { data } = await api.post('/api/report', {
      mission_id,
      stats
    })
    return data
  },

  /**
   * 生成“智能体分析控制台”输出（模板/LLM）
   */
  async getAnalysis(mission_id, stats) {
    const payload = {
      mission_id
    }
    if (stats) payload.stats = stats
    const { data } = await api.post('/api/analyze', payload)
    return data
  },

  /**
   * 触发缓存导出
   */
  async exportCache(mode, location) {
    const { data } = await api.post('/api/cache/export', {
      mode,
      location
    })
    return data
  },

  /**
   * 健康检查
   */
  async healthCheck() {
    const { data } = await api.get('/health')
    return data
  }
}
