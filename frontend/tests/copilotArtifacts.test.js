import { describe, it, expect } from 'vitest'
import { applyCopilotArtifacts } from '../src/utils/copilotArtifacts.js'

function baseState() {
  return {
    layers: [
      { id: 'ai-imagery', name: 'AI Imagery Overlay', enabled: false, params: { opacity: 0.5, tile_url: '' } },
      { id: 'ai-vector', name: 'AI Vector Overlay', enabled: false, params: { opacity: 0.9, geojson: null } },
    ],
    charts: [],
    code: '',
    report: '',
  }
}

describe('applyCopilotArtifacts (Phase 1 gate)', () => {
  it('writes code + report', () => {
    const next = applyCopilotArtifacts(baseState(), [
      { type: 'tool_call', tool: 'write_to_editor', args: { code: 'print(123)' } },
      { type: 'tool_call', tool: 'generate_report', args: { text: '# Brief\nOK' } },
    ])

    expect(next.code).toContain('print(123)')
    expect(next.report).toContain('# Brief')
  })

  it('installs AI imagery and vector overlays', () => {
    const geojson = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { id: 1 },
          geometry: {
            type: 'Polygon',
            coordinates: [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
          },
        },
      ],
    }

    const next = applyCopilotArtifacts(baseState(), [
      {
        type: 'tool_call',
        tool: 'add_cesium_imagery',
        args: { tile_url: '/api/basemap/osm/{z}/{x}/{y}.png', opacity: 0.66, palette: 'Oranges', threshold: 0.4 },
      },
      {
        type: 'tool_call',
        tool: 'add_cesium_vector',
        args: { geojson, opacity: 0.8, color: '#FF4D6D' },
      },
    ])

    const img = next.layers.find((l) => l.id === 'ai-imagery')
    const vec = next.layers.find((l) => l.id === 'ai-vector')

    expect(img?.enabled).toBe(true)
    expect(String(img?.params?.tile_url || '')).toContain('/api/basemap/osm/')
    expect(img?.params?.opacity).toBeCloseTo(0.66)

    expect(vec?.enabled).toBe(true)
    expect(vec?.params?.geojson?.type).toBe('FeatureCollection')
    expect(vec?.params?.color).toBe('#FF4D6D')
  })

  it('appends chart artifacts', () => {
    const next = applyCopilotArtifacts(baseState(), [
      { type: 'tool_call', tool: 'show_chart', args: { kind: 'scatter', title: 'Income vs LST', data: { points: [1, 2, 3] } } },
      { type: 'tool_call', tool: 'render_bivariate_map', args: { title: 'Bivariate Grid', data: { grid: [] } } },
    ])

    expect(next.charts.length).toBe(2)
    expect(next.charts[0].title).toContain('Income')
    expect(next.charts[1].kind).toBe('bivariate')
  })
})
