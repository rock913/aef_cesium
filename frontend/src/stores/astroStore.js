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
  const { mode, maxComputeInvocationsPerWorkgroup, currentAgentAction, aionModelState } = toRefs(state)

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

  return {
    mode,
    maxComputeInvocationsPerWorkgroup,
    currentAgentAction,
    aionModelState,

    setMode,
    setMaxComputeInvocationsPerWorkgroup,
    dispatchAgentAction,
    clearCurrentAgentAction,

    setGenerating,
    setLastError,
  }
}

export function __resetAstroStoreForTests() {
  state.mode = DEFAULT_ASTRO_MODE
  state.maxComputeInvocationsPerWorkgroup = 0
  state.currentAgentAction = null
  state.aionModelState.isGenerating = false
  state.aionModelState.lastError = ''
}
