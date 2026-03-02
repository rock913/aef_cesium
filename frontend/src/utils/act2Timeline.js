// Act-2 scrollytelling timeline helpers.
// IMPORTANT: No direct Cesium imports. Operates on CesiumViewer public API only.

export const ACT2_STEPS = Object.freeze(['space', 'earth', 'target', 'summary'])

export function normalizeAct2StepId(stepId) {
  const s = String(stepId || '').trim().toLowerCase()
  if (!s) return ''
  if (ACT2_STEPS.includes(s)) return s
  return ''
}

export function getAct2StepIndex(stepId) {
  const id = normalizeAct2StepId(stepId)
  if (!id) return -1
  return ACT2_STEPS.indexOf(id)
}

export function getNextAct2Step(stepId) {
  const idx = getAct2StepIndex(stepId)
  if (idx < 0) return 'space'
  return ACT2_STEPS[Math.min(ACT2_STEPS.length - 1, idx + 1)]
}

export function getPrevAct2Step(stepId) {
  const idx = getAct2StepIndex(stepId)
  if (idx < 0) return 'space'
  return ACT2_STEPS[Math.max(0, idx - 1)]
}

export function resolveAct2Target(choreoName) {
  const name = String(choreoName || '').trim().toLowerCase()

  // Extendable target catalog.
  // Heights are intentionally coarse so it works across imagery sources.
  const targets = {
    poyang: { lat: 29.12, lon: 116.23, height: 35_000 },
    // Jiangsu Yancheng wetlands region (approx)
    yancheng: { lat: 33.38, lon: 120.13, height: 40_000 },
    // Yangtze River Delta / Shanghai region (approx)
    yangtze: { lat: 31.23, lon: 121.47, height: 45_000 },
  }

  if (name && targets[name]) return targets[name]
  return targets.poyang
}

function _safeCall(fn, ...args) {
  try {
    return fn?.(...args)
  } catch (_) {
    return undefined
  }
}

export function applyAct2Step(viewerApi, stepId, choreoName) {
  const step = normalizeAct2StepId(stepId)
  if (!viewerApi || !step) return false

  const deepSpace = { lat: 35.0, lon: 105.0, height: 45_000_000 }
  const earthOrbit = { lat: 30.0, lon: 110.0, height: 3_200_000 }
  const target = resolveAct2Target(choreoName)

  // Best-effort stabilization.
  _safeCall(viewerApi.stopGlobalRotation?.bind(viewerApi))

  if (step === 'space') {
    _safeCall(viewerApi.flyTo?.bind(viewerApi), deepSpace, 1.2, () => {
      _safeCall(viewerApi.startGlobalRotation?.bind(viewerApi))
    })
    return true
  }

  if (step === 'earth') {
    _safeCall(viewerApi.flyTo?.bind(viewerApi), earthOrbit, 2.0)
    return true
  }

  if (step === 'target') {
    _safeCall(viewerApi.flyTo?.bind(viewerApi), target, 3.0)
    return true
  }

  if (step === 'summary') {
    const recap = { lat: target.lat, lon: target.lon, height: 1_100_000 }
    _safeCall(viewerApi.flyTo?.bind(viewerApi), recap, 1.6)
    return true
  }

  return false
}

export function pickDominantAct2Entry(entries) {
  const list = Array.isArray(entries) ? entries : []
  let best = null
  for (const e of list) {
    if (!e || !e.isIntersecting) continue
    if (!best) {
      best = e
      continue
    }
    const a = Number(e.intersectionRatio || 0)
    const b = Number(best.intersectionRatio || 0)
    if (a > b) best = e
  }
  return best
}
