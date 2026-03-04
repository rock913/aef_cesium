/**
 * Apply v7 tool-calling events to Workbench artifacts.
 *
 * This is intentionally pure and unit-testable so we can gate regressions
 * without spinning up Vue/Cesium.
 */

function clamp01(n, fallback = undefined) {
  const x = Number(n)
  if (!Number.isFinite(x)) return fallback
  return Math.max(0, Math.min(1, x))
}

function upsertLayer(layers, id, patch) {
  const a = Array.isArray(layers) ? layers : []
  const idx = a.findIndex((l) => String(l?.id || '') === id)
  if (idx >= 0) {
    const cur = a[idx] || {}
    const next = typeof patch === 'function' ? patch(cur) : { ...cur, ...(patch || {}) }
    const out = [...a]
    out[idx] = next
    return out
  }
  const base = { id, name: id, enabled: true, params: {} }
  const next = typeof patch === 'function' ? patch(base) : { ...base, ...(patch || {}) }
  return [...a, next]
}

export function applyCopilotArtifacts(prev, events) {
  const state = prev && typeof prev === 'object' ? prev : {}
  const arr = Array.isArray(events) ? events : []

  let layers = Array.isArray(state.layers) ? state.layers : []
  let charts = Array.isArray(state.charts) ? state.charts : []
  let code = String(state.code ?? '')
  let report = String(state.report ?? '')

  for (const e of arr) {
    if (!e || e.type !== 'tool_call') continue
    const tool = String(e.tool || '').trim()
    const args = e && typeof e === 'object' ? e.args : null

    if (tool === 'write_to_editor') {
      const nextCode = String(args?.code || '').trim()
      if (nextCode) code = nextCode
      continue
    }

    if (tool === 'generate_report') {
      const t = String(args?.text || '').trim()
      if (t) report = t
      continue
    }

    if (tool === 'add_cesium_imagery') {
      const tileUrl = String(args?.tile_url || args?.url || '').trim()
      const opacity = clamp01(args?.opacity)
      const threshold = clamp01(args?.threshold)
      const palette = String(args?.palette || '').trim()

      layers = upsertLayer(layers, 'ai-imagery', (cur) => {
        const params = { ...(cur.params || {}) }
        if (tileUrl) params.tile_url = tileUrl
        if (opacity !== undefined) params.opacity = opacity
        if (threshold !== undefined) params.threshold = threshold
        if (palette) params.palette = palette
        return { ...cur, enabled: true, params, name: cur.name || 'AI Imagery Overlay' }
      })
      continue
    }

    if (tool === 'add_cesium_vector') {
      const geojson = args?.geojson ?? null
      const opacity = clamp01(args?.opacity)
      const color = String(args?.color || '').trim()

      layers = upsertLayer(layers, 'ai-vector', (cur) => {
        const params = { ...(cur.params || {}) }
        params.geojson = geojson
        if (opacity !== undefined) params.opacity = opacity
        if (color) params.color = color
        return { ...cur, enabled: true, params, name: cur.name || 'AI Vector Overlay' }
      })
      continue
    }

    if (tool === 'show_chart' || tool === 'render_bivariate_map') {
      const kind = String(args?.kind || (tool === 'render_bivariate_map' ? 'bivariate' : 'chart')).trim() || 'chart'
      const title = String(args?.title || '').trim() || (tool === 'render_bivariate_map' ? 'Bivariate Map' : 'Chart')
      const data = args?.data ?? args ?? null
      const id = `${tool}:${Date.now()}:${Math.random().toString(16).slice(2)}`
      charts = [...charts, { id, kind, title, data }]
      continue
    }
  }

  return { layers, charts, code, report }
}
