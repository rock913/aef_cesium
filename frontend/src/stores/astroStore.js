import { reactive, toRefs } from 'vue'

// AI-Native action bus for OneAstronomy (v7.5).
//
// Contract:
// - Business actions must be emitted as `currentAgentAction` updates.
// - UI should not add buttons on top of 3D canvases; existing Workbench panels
//   can dispatch actions into this store.

export const ASTRO_MODES = Object.freeze(['webgpu', 'fallback'])
export const DEFAULT_ASTRO_MODE = 'webgpu'

// Keep action types stringly-typed on purpose: it plays well with LLM prompts
// and allows incremental migration to TS later.
export const ASTRO_AGENT_ACTION_TYPES = Object.freeze({
  // Scene 0 (handover)
  REQUEST_HANDOVER_TO_DEEP_SPACE: 'REQUEST_HANDOVER_TO_DEEP_SPACE',

  // Demo 1 (CSST decomposition)
  DECOMPOSE_CSST_GALAXY: 'DECOMPOSE_CSST_GALAXY',
  STOP_CSST_DECOMPOSITION: 'STOP_CSST_DECOMPOSITION',

  // Scene 1
  EXECUTE_REDSHIFT_PREDICTION: 'EXECUTE_REDSHIFT_PREDICTION',

  // Scene 2
  SEARCH_SIMILAR_LENS: 'SEARCH_SIMILAR_LENS',

  // Demo 3 (GOTTA)
  CAPTURE_TRANSIENT_EVENT: 'CAPTURE_TRANSIENT_EVENT',

  // Demo 4
  START_MODAL_INPAINT: 'START_MODAL_INPAINT',
  STOP_MODAL_INPAINT: 'STOP_MODAL_INPAINT',

  // Phase 2.5: continuous narrative (4 acts)
  EXECUTE_ONEASTRO_STORY_FLOW: 'EXECUTE_ONEASTRO_STORY_FLOW',
  STOP_ONEASTRO_STORY_FLOW: 'STOP_ONEASTRO_STORY_FLOW',

  // Scene 4
  SIMULATE_GALAXY_COLLISION: 'SIMULATE_GALAXY_COLLISION',
})

// Astro-GIS layer ids (Phase 1-3).
// Keep them stringly-typed and stable: they are referenced by the LayerTree UI,
// ThreeTwin mappings, and tests.
export const ASTRO_GIS_LAYER_IDS = Object.freeze({
  MACRO_SDSS: 'astro-macro-sdss',
  DEMO_CSST: 'astro-demo-csst',
  DEMO_GOTTA: 'astro-demo-gotta',
  DEMO_INPAINT: 'astro-demo-inpaint',
  HIPS_BACKGROUND: 'astro-hips-background',
  CATALOG_SIMBAD: 'astro-catalog-simbad',
})

let _nextActionId = 1

const state = reactive({
  mode: DEFAULT_ASTRO_MODE,

  // WebGPU capability probe results (optional; can be populated by ThreeTwin).
  maxComputeInvocationsPerWorkgroup: 0,

  // Action bus: watchers should react to actionId changes.
  currentAgentAction: null,

  // Model/runtime state used by shader-driven scenes.
  aionModelState: {
    isGenerating: false,
    lastError: '',
  },

  // Astro-GIS: Layer state tree (Foundation for Phase 1-3).
  // ThreeTwin should treat this as the source of truth for sky-layer authority.
  astroGis: {
    // A bump-only value that watchers can use to cheaply detect changes.
    version: 1,
    layers: {
      [ASTRO_GIS_LAYER_IDS.MACRO_SDSS]: {
        id: ASTRO_GIS_LAYER_IDS.MACRO_SDSS,
        name: 'Macro SDSS (Cosmic Web)',
        visible: true,
        opacity: 1.0,
        style: { pointSize: 15.0 },
        source: { kind: 'sdss_micro_sample', path: '/data/astronomy/sdss_micro_sample.json' },
      },
      [ASTRO_GIS_LAYER_IDS.DEMO_CSST]: {
        id: ASTRO_GIS_LAYER_IDS.DEMO_CSST,
        name: 'Demo CSST',
        visible: true,
        opacity: 1.0,
        style: {},
        source: { kind: 'internal' },
      },
      [ASTRO_GIS_LAYER_IDS.DEMO_GOTTA]: {
        id: ASTRO_GIS_LAYER_IDS.DEMO_GOTTA,
        name: 'Demo GOTTA',
        visible: true,
        opacity: 1.0,
        style: {},
        source: { kind: 'mock', path: '/data/astronomy/gotta_transient_event.json' },
      },
      [ASTRO_GIS_LAYER_IDS.DEMO_INPAINT]: {
        id: ASTRO_GIS_LAYER_IDS.DEMO_INPAINT,
        name: 'Demo Inpaint',
        visible: true,
        opacity: 1.0,
        style: {},
        source: { kind: 'internal' },
      },
      [ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND]: {
        id: ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND,
        name: 'HiPS Background',
        visible: false,
        opacity: 1.0,
        style: {
          // Best-effort; concrete mapping lives in the Aladin adapter.
          survey: 'P/DSS2/color',
          fovSync: true,
        },
        source: { kind: 'hips', provider: 'aladin-lite-v3' },
      },
      [ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD]: {
        id: ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD,
        name: 'Catalog: SIMBAD',
        visible: false,
        opacity: 1.0,
        style: { maxRows: 600, minMag: null },
        source: { kind: 'catalog', provider: 'simbad', endpoint: '/api/astro-gis/catalog/simbad' },
      },
    },
  },
})

function _assertMode(mode) {
  const v = String(mode || '').trim().toLowerCase()
  if (!ASTRO_MODES.includes(v)) throw new Error(`Unknown astro mode: ${mode}`)
  return v
}

function _normalizeAction(action) {
  if (!action || typeof action !== 'object') throw new Error('Action must be an object')
  const type = String(action.type || '').trim()
  if (!type) throw new Error('Action.type is required')

  return {
    actionId: _nextActionId++,
    type,
    payload: action.payload ?? null,
    meta: {
      createdAt: Date.now(),
      ...(action.meta && typeof action.meta === 'object' ? action.meta : null),
    },
  }
}

export function useAstroStore() {
  const { mode, maxComputeInvocationsPerWorkgroup, currentAgentAction, aionModelState, astroGis } = toRefs(state)

  function setMode(nextMode) {
    mode.value = _assertMode(nextMode)
  }

  function setMaxComputeInvocationsPerWorkgroup(v) {
    const n = Number(v)
    maxComputeInvocationsPerWorkgroup.value = Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0
  }

  function dispatchAgentAction(action) {
    currentAgentAction.value = _normalizeAction(action)
    return currentAgentAction.value.actionId
  }

  function clearCurrentAgentAction() {
    currentAgentAction.value = null
  }

  function setGenerating(isGenerating) {
    aionModelState.value.isGenerating = !!isGenerating
  }

  function setLastError(msg) {
    aionModelState.value.lastError = String(msg || '')
  }

  function _bumpAstroGisVersion() {
    try {
      astroGis.value.version = (Number(astroGis.value.version) || 0) + 1
    } catch (_) {
      // ignore
    }
  }

  function getAstroGisLayer(id) {
    const key = String(id || '').trim()
    if (!key) return null
    const layers = astroGis.value?.layers || null
    return (layers && typeof layers === 'object') ? (layers[key] || null) : null
  }

  function setAstroGisLayerVisible(id, visible) {
    const layer = getAstroGisLayer(id)
    if (!layer) return false
    layer.visible = !!visible
    _bumpAstroGisVersion()
    return true
  }

  function setAstroGisLayerOpacity(id, opacity) {
    const layer = getAstroGisLayer(id)
    if (!layer) return false
    const n = Number(opacity)
    layer.opacity = Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : layer.opacity
    _bumpAstroGisVersion()
    return true
  }

  function patchAstroGisLayer(id, patch) {
    const layer = getAstroGisLayer(id)
    if (!layer) return false
    if (!patch || typeof patch !== 'object') return false
    if (patch.visible !== undefined) layer.visible = !!patch.visible
    if (patch.opacity !== undefined) {
      const n = Number(patch.opacity)
      if (Number.isFinite(n)) layer.opacity = Math.max(0, Math.min(1, n))
    }
    if (patch.style && typeof patch.style === 'object') layer.style = { ...(layer.style || {}), ...patch.style }
    if (patch.source && typeof patch.source === 'object') layer.source = { ...(layer.source || {}), ...patch.source }
    _bumpAstroGisVersion()
    return true
  }

  return {
    mode,
    maxComputeInvocationsPerWorkgroup,
    currentAgentAction,
    aionModelState,
    astroGis,

    setMode,
    setMaxComputeInvocationsPerWorkgroup,
    dispatchAgentAction,
    clearCurrentAgentAction,

    setGenerating,
    setLastError,

    // Astro-GIS layer store (Phase 1-3)
    getAstroGisLayer,
    setAstroGisLayerVisible,
    setAstroGisLayerOpacity,
    patchAstroGisLayer,
  }
}

export function __resetAstroStoreForTests() {
  state.mode = DEFAULT_ASTRO_MODE
  state.maxComputeInvocationsPerWorkgroup = 0
  state.currentAgentAction = null
  state.aionModelState.isGenerating = false
  state.aionModelState.lastError = ''

  // Reset Astro-GIS layer state.
  try {
    const layers = state.astroGis?.layers
    if (layers && typeof layers === 'object') {
      for (const k of Object.keys(layers)) {
        const l = layers[k]
        if (!l || typeof l !== 'object') continue
        if (k === ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND || k === ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD) {
          l.visible = false
        } else {
          l.visible = true
        }
        l.opacity = 1.0
      }
    }
    state.astroGis.version = 1
  } catch (_) {
    // ignore
  }
}
