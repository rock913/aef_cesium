import { reactive, toRefs } from 'vue'

export const SCALES = Object.freeze(['earth', 'macro', 'micro'])
export const DEFAULT_SCALE = 'earth'

const state = reactive({
  currentScale: DEFAULT_SCALE,
})

function _assertScale(scale) {
  const v = String(scale || '').trim().toLowerCase()
  if (!SCALES.includes(v)) {
    throw new Error(`Unknown scale: ${scale}`)
  }
  return v
}

export function useResearchStore() {
  const { currentScale } = toRefs(state)

  function setScale(scale) {
    currentScale.value = _assertScale(scale)
  }

  return {
    currentScale,
    setScale,
  }
}

export function __resetResearchStoreForTests() {
  state.currentScale = DEFAULT_SCALE
}
