import { describe, expect, it } from 'vitest'
import { mapLayersToThreeParams, THREE_LAYER_DEFAULTS } from '../src/views/workbench/engines/threeLayerMapping.js'

describe('mapLayersToThreeParams (Milestone 3)', () => {
  it('derives bloom params and visibility/material params from layers', () => {
    const layers = [
      { id: 'bloom', enabled: true, params: { strength: 1.8, threshold: 0.66, radius: 0.22 } },
      { id: 'macro-spiral', enabled: false },
      { id: 'micro-atoms', enabled: true, params: { opacity: 0.5, transmission: 0.9, ior: 1.6 } },
    ]

    const out = mapLayersToThreeParams(layers)

    expect(out.bloom.enabled).toBe(true)
    expect(out.bloom.strength).toBe(1.8)
    expect(out.bloom.threshold).toBe(0.66)
    expect(out.bloom.radius).toBe(0.22)

    expect(out.macroSpiralVisible).toBe(false)
    expect(out.microAtomsVisible).toBe(true)
    expect(out.terminatorShieldVisible).toBe(false)

    expect(out.microMaterial.opacity).toBe(0.5)
    expect(out.microMaterial.transmission).toBe(0.9)
    expect(out.microMaterial.ior).toBe(1.6)
  })

  it('hides the macro spiral when terminator shield is enabled', () => {
    const out = mapLayersToThreeParams([
      { id: 'macro-spiral', enabled: true },
      { id: 'terminator-shield', enabled: true },
    ])

    expect(out.terminatorShieldVisible).toBe(true)
    expect(out.macroSpiralVisible).toBe(false)
  })

  it('falls back to defaults for missing/invalid params', () => {
    const out = mapLayersToThreeParams([{ id: 'bloom', enabled: true, params: { strength: 'nope' } }])
    expect(out.bloom.strength).toBe(THREE_LAYER_DEFAULTS.bloom.strength)
  })
})
