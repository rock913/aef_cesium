// Lightweight choreography helpers.
// IMPORTANT: This file intentionally does not import Cesium directly.
// It operates on the public methods exposed by the CesiumViewer component
// (e.g. flyTo/startGlobalRotation/stopGlobalRotation) so it remains testable.

export function buildDemoChoreoHref(choreoName) {
  const name = String(choreoName || '').trim()
  if (!name) return '/demo'
  return `/demo?choreo=${encodeURIComponent(name)}`
}

export function buildAct2ChoreoHref(choreoName) {
  const name = String(choreoName || '').trim()
  if (!name) return '/act2'
  return `/act2?choreo=${encodeURIComponent(name)}`
}

export function getChoreoFromSearch(search) {
  const raw = typeof search === 'string' ? search : ''
  const s = raw.startsWith('?') ? raw.slice(1) : raw
  if (!s) return ''

  try {
    const sp = new URLSearchParams(s)
    return String(sp.get('choreo') || '').trim().toLowerCase()
  } catch (_) {
    return ''
  }
}

function _safeCall(fn, ...args) {
  try {
    return fn?.(...args)
  } catch (_) {
    return undefined
  }
}

export function runPoyangChoreo(viewerApi) {
  // Minimal “deep space -> Earth -> Poyang” feel.
  // NOTE: We use lat/lon/height only so it works with our CesiumViewer wrapper.
  if (!viewerApi || typeof viewerApi.flyTo !== 'function') return false

  _safeCall(viewerApi.stopGlobalRotation?.bind(viewerApi))

  const deepSpace = { lat: 35.0, lon: 105.0, height: 45_000_000 }
  const poyang = { lat: 29.12, lon: 116.23, height: 35_000 }

  // Chain using CesiumViewer's callback signature: flyTo(target, duration_s, onComplete)
  _safeCall(viewerApi.flyTo?.bind(viewerApi), deepSpace, 1.6, () => {
    _safeCall(viewerApi.flyTo?.bind(viewerApi), poyang, 3.6)
  })

  return true
}

export function runChoreo(viewerApi, choreoName) {
  const name = String(choreoName || '').trim().toLowerCase()
  if (!name) return false

  if (name === 'poyang') return runPoyangChoreo(viewerApi)
  return false
}
