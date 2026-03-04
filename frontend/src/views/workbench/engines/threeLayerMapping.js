export const THREE_LAYER_DEFAULTS = Object.freeze({
  bloom: Object.freeze({
    enabled: true,
    strength: 1.1,
    threshold: 0.65,
    radius: 0.15,
  }),
  microMaterial: Object.freeze({
    opacity: 0.85,
    transmission: 0.85,
    ior: 1.4,
  }),
  macroSpiralVisible: true,
  microAtomsVisible: true,
})

function _num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function _clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n))
}

function _findLayer(layers, id) {
  const key = String(id || '')
  return (Array.isArray(layers) ? layers : []).find((l) => String(l?.id || '') === key) || null
}

export function mapLayersToThreeParams(layers) {
  const bloomLayer = _findLayer(layers, 'bloom')
  const macroLayer = _findLayer(layers, 'macro-spiral')
  const microLayer = _findLayer(layers, 'micro-atoms')

  const bloomEnabled = bloomLayer ? !!bloomLayer.enabled : THREE_LAYER_DEFAULTS.bloom.enabled
  const bloomP = bloomLayer?.params || {}

  const strength = _num(bloomP.strength)
  const threshold = _num(bloomP.threshold)
  const radius = _num(bloomP.radius)

  const microEnabled = microLayer ? !!microLayer.enabled : THREE_LAYER_DEFAULTS.microAtomsVisible
  const microP = microLayer?.params || {}

  const opacity = _num(microP.opacity)
  const transmission = _num(microP.transmission)
  const ior = _num(microP.ior)

  return {
    bloom: {
      enabled: bloomEnabled,
      strength: strength === null ? THREE_LAYER_DEFAULTS.bloom.strength : _clamp(strength, 0, 3),
      threshold: threshold === null ? THREE_LAYER_DEFAULTS.bloom.threshold : _clamp(threshold, 0, 1),
      radius: radius === null ? THREE_LAYER_DEFAULTS.bloom.radius : _clamp(radius, 0, 1),
    },
    macroSpiralVisible: macroLayer ? !!macroLayer.enabled : THREE_LAYER_DEFAULTS.macroSpiralVisible,
    microAtomsVisible: microEnabled,
    microMaterial: {
      opacity: opacity === null ? THREE_LAYER_DEFAULTS.microMaterial.opacity : _clamp(opacity, 0, 1),
      transmission: transmission === null ? THREE_LAYER_DEFAULTS.microMaterial.transmission : _clamp(transmission, 0, 1),
      ior: ior === null ? THREE_LAYER_DEFAULTS.microMaterial.ior : _clamp(ior, 1, 2),
    },
  }
}
