import { describe, it, expect } from 'vitest'
import {
  computeClusterStats,
  defaultGalaxyClusters,
  generateGalaxyNodes,
  matchGalaxyQuery,
  normalizeQuery,
} from '../src/utils/galaxy.js'

describe('galaxy utils', () => {
  it('normalizes query', () => {
    expect(normalizeQuery('  POYANG ')).toBe('poyang')
    expect(normalizeQuery(null)).toBe('')
  })

  it('generates deterministic nodes and stats', () => {
    const clusters = defaultGalaxyClusters()
    const a = generateGalaxyNodes({ seed: 21, count: 900, clusters })
    const b = generateGalaxyNodes({ seed: 21, count: 900, clusters })

    expect(a.length).toBe(900)
    expect(b.length).toBe(900)

    // Deterministic first node id and cluster
    expect(a[0].id).toBe(b[0].id)
    expect(a[0].clusterId).toBe(b[0].clusterId)

    const stats = computeClusterStats(a, clusters)
    expect(Object.keys(stats).length).toBe(clusters.length)
    for (const c of clusters) {
      expect(stats[c.id].count).toBeGreaterThan(0)
      expect(stats[c.id].cx).toEqual(expect.any(Number))
      expect(stats[c.id].cy).toEqual(expect.any(Number))
    }
  })

  it('matches friendly aliases', () => {
    const clusters = defaultGalaxyClusters()
    expect(matchGalaxyQuery('poyang', clusters)).toBe('wetlands')
    expect(matchGalaxyQuery('鄱阳湖', clusters)).toBe('wetlands')
    expect(matchGalaxyQuery('hydrology', clusters)).toBe('hydrology')
    expect(matchGalaxyQuery('水文变化', clusters)).toBe('hydrology')
  })
})
