import { describe, expect, it } from 'vitest'
import { applyCopilotArtifacts } from '../src/utils/copilotArtifacts.js'

describe('applyCopilotArtifacts (Phase 3)', () => {
  it('records terrain, 3d tiles, scene mode and globe transparency', () => {
    const prev = { layers: [], charts: [], code: '', report: '' }
    const next = applyCopilotArtifacts(prev, [
      { type: 'tool_call', tool: 'enable_3d_terrain', args: { terrain: 'cesium_world_terrain' } },
      { type: 'tool_call', tool: 'add_cesium_3d_tiles', args: { name: 'Everest', url: 'https://example.com/tileset.json', opacity: 0.8 } },
      { type: 'tool_call', tool: 'set_scene_mode', args: { mode: 'night' } },
      { type: 'tool_call', tool: 'set_globe_transparency', args: { alpha: 0.5 } },
    ])

    const ids = new Set((next.layers || []).map((l) => l.id))
    expect(ids.has('terrain')).toBe(true)
    expect(ids.has('3d-tiles')).toBe(true)
    expect(ids.has('scene-mode')).toBe(true)
    expect(ids.has('globe-transparency')).toBe(true)
  })

  it('records wormhole and appends a small report line', () => {
    const prev = { layers: [], charts: [], code: '', report: '' }
    const next = applyCopilotArtifacts(prev, [
      { type: 'tool_call', tool: 'trigger_gsap_wormhole', args: { target: 'micro' } },
    ])

    const ids = new Set((next.layers || []).map((l) => l.id))
    expect(ids.has('wormhole')).toBe(true)
    expect(String(next.report || '')).toContain('Wormhole')
    expect(String(next.report || '')).toContain('micro')
  })
})
