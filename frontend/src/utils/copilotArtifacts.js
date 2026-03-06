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

function _asString(v) {
  return String(v ?? '').trim()
}

function _safeJson(v) {
  try {
    return JSON.stringify(v)
  } catch (_) {
    return ''
  }
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

    // Phase 3: keep tool outputs visible/deterministic even when the engine
    // implementation is stubbed.
    if (tool === 'enable_3d_terrain') {
      const terrain = _asString(args?.terrain || 'cesium_world_terrain') || 'cesium_world_terrain'
      layers = upsertLayer(layers, 'terrain', (cur) => {
        const params = { ...(cur.params || {}) }
        params.terrain = terrain
        return { ...cur, enabled: true, params, name: cur.name || '3D Terrain' }
      })
      continue
    }

    if (tool === 'add_cesium_3d_tiles') {
      const name = _asString(args?.name || '') || '3D Tiles'
      const url = _asString(args?.url || '')
      const ionAssetId = args?.ion_asset_id
      const opacity = clamp01(args?.opacity)
      layers = upsertLayer(layers, '3d-tiles', (cur) => {
        const params = { ...(cur.params || {}) }
        params.name = name
        if (url) params.url = url
        if (ionAssetId !== undefined && ionAssetId !== null) params.ion_asset_id = ionAssetId
        if (opacity !== undefined) params.opacity = opacity
        return { ...cur, enabled: true, params, name }
      })
      continue
    }

    if (tool === 'add_cesium_extruded_polygons') {
      const height = Number(args?.height)
      const color = _asString(args?.color || '#00F0FF') || '#00F0FF'
      const opacity = clamp01(args?.opacity)
      layers = upsertLayer(layers, 'extruded-polygons', (cur) => {
        const params = { ...(cur.params || {}) }
        params.geojson = args?.geojson ?? null
        if (Number.isFinite(height)) params.height = height
        if (color) params.color = color
        if (opacity !== undefined) params.opacity = opacity
        return { ...cur, enabled: true, params, name: cur.name || 'Extruded Polygons' }
      })
      continue
    }

    if (tool === 'apply_custom_shader' || tool === 'generate_cesium_custom_shader') {
      const kind = _asString(args?.kind || '') || (tool === 'generate_cesium_custom_shader' ? 'cesium_custom_shader' : 'custom_shader')
      layers = upsertLayer(layers, 'custom-shader', (cur) => {
        const params = { ...(cur.params || {}) }
        params.kind = kind
        params.params = args?.params ?? null
        params.last_tool = tool
        return { ...cur, enabled: true, params, name: cur.name || 'Custom Shader' }
      })
      const maybeCode = _asString(args?.code || '')
      if (maybeCode) code = maybeCode
      continue
    }

    if (tool === 'set_scene_mode') {
      const mode = _asString(args?.mode || 'day').toLowerCase() || 'day'
      layers = upsertLayer(layers, 'scene-mode', (cur) => {
        const params = { ...(cur.params || {}) }
        params.mode = mode
        return { ...cur, enabled: true, params, name: cur.name || 'Scene Mode' }
      })
      continue
    }

    if (tool === 'play_czml_animation') {
      const czmlUrl = _asString(args?.czml_url || '')
      const speed = Number(args?.speed)
      layers = upsertLayer(layers, 'czml', (cur) => {
        const params = { ...(cur.params || {}) }
        if (czmlUrl) params.czml_url = czmlUrl
        params.czml = args?.czml ?? null
        if (Number.isFinite(speed)) params.speed = speed
        return { ...cur, enabled: true, params, name: cur.name || 'CZML Animation' }
      })
      continue
    }

    if (tool === 'set_globe_transparency') {
      const alpha = Number(args?.alpha)
      layers = upsertLayer(layers, 'globe-transparency', (cur) => {
        const params = { ...(cur.params || {}) }
        if (Number.isFinite(alpha)) params.alpha = alpha
        return { ...cur, enabled: true, params, name: cur.name || 'Globe Transparency' }
      })
      continue
    }

    if (tool === 'add_subsurface_model') {
      const name = _asString(args?.name || '') || 'Subsurface Model'
      const url = _asString(args?.url || '')
      const opacity = clamp01(args?.opacity)
      layers = upsertLayer(layers, 'subsurface', (cur) => {
        const params = { ...(cur.params || {}) }
        if (name) params.name = name
        if (url) params.url = url
        if (opacity !== undefined) params.opacity = opacity
        return { ...cur, enabled: true, params, name }
      })
      continue
    }

    if (tool === 'trigger_gsap_wormhole') {
      const target = _asString(args?.target || 'micro') || 'micro'
      layers = upsertLayer(layers, 'wormhole', (cur) => {
        const params = { ...(cur.params || {}) }
        params.target = target
        return { ...cur, enabled: true, params, name: cur.name || 'Wormhole Transition' }
      })
      // Also surface as a tiny report append (deterministic text).
      if (!report) report = '# Wormhole\n'
      report = report + `\n- Wormhole: ${target}\n`
      continue
    }
  }

  return { layers, charts, code, report }
}
