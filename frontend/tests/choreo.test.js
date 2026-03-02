import { describe, it, expect, vi } from 'vitest'
import { buildAct2ChoreoHref, buildDemoChoreoHref, getChoreoFromSearch, runChoreo } from '../src/utils/choreo.js'

describe('choreography helpers', () => {
  it('builds /demo choreo hrefs', () => {
    expect(buildDemoChoreoHref('')).toBe('/demo')
    expect(buildDemoChoreoHref('poyang')).toBe('/demo?choreo=poyang')
  })

  it('builds /act2 choreo hrefs', () => {
    expect(buildAct2ChoreoHref('')).toBe('/act2')
    expect(buildAct2ChoreoHref('poyang')).toBe('/act2?choreo=poyang')
  })

  it('parses choreo from query string', () => {
    expect(getChoreoFromSearch('')).toBe('')
    expect(getChoreoFromSearch('?choreo=poyang')).toBe('poyang')
    expect(getChoreoFromSearch('choreo=POYANG')).toBe('poyang')
    expect(getChoreoFromSearch('?x=1&choreo=poyang&y=2')).toBe('poyang')
  })

  it('runs poyang choreo against a viewer stub', () => {
    const calls = []

    const viewerApi = {
      stopGlobalRotation: vi.fn(),
      flyTo: (loc, durationS, onComplete) => {
        calls.push({ loc, durationS })
        if (typeof onComplete === 'function') onComplete()
      },
    }

    const ok = runChoreo(viewerApi, 'poyang')
    expect(ok).toBe(true)
    expect(viewerApi.stopGlobalRotation).toHaveBeenCalledTimes(1)
    expect(calls.length).toBe(2)

    // deep-space style first, then target area
    expect(calls[0].loc).toHaveProperty('height')
    expect(calls[1].loc).toMatchObject({ lat: expect.any(Number), lon: expect.any(Number) })
  })

  it('is safe when viewerApi is missing', () => {
    expect(runChoreo(null, 'poyang')).toBe(false)
    expect(runChoreo({}, 'poyang')).toBe(false)
  })
})
