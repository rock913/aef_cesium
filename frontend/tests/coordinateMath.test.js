import { describe, it, expect } from 'vitest'
import {
  raDecToUnitVector,
  unitVectorToRaDec,
  logScaleDistance,
  raDecDistanceToCartesian,
} from '../src/utils/astronomy/coordinateMath.js'

describe('coordinateMath', () => {
  it('converts RA/Dec to expected unit vectors', () => {
    const v0 = raDecToUnitVector(0, 0)
    expect(v0.x).toBeCloseTo(1, 6)
    expect(v0.y).toBeCloseTo(0, 6)
    expect(v0.z).toBeCloseTo(0, 6)

    const v90 = raDecToUnitVector(90, 0)
    expect(v90.x).toBeCloseTo(0, 6)
    expect(v90.y).toBeCloseTo(1, 6)
    expect(v90.z).toBeCloseTo(0, 6)

    const vN = raDecToUnitVector(123, 90)
    expect(vN.z).toBeCloseTo(1, 6)

    const vS = raDecToUnitVector(123, -90)
    expect(vS.z).toBeCloseTo(-1, 6)
  })

  it('inverts unit vector back to RA/Dec', () => {
    const { raDeg, decDeg } = unitVectorToRaDec({ x: 0, y: 1, z: 0 })
    expect(raDeg).toBeCloseTo(90, 6)
    expect(decDeg).toBeCloseTo(0, 6)
  })

  it('log-scales distances monotonically', () => {
    expect(logScaleDistance(0)).toBeCloseTo(0, 12)
    expect(logScaleDistance(10)).toBeGreaterThan(logScaleDistance(1))
    expect(logScaleDistance(100)).toBeGreaterThan(logScaleDistance(10))
  })

  it('maps RA/Dec/Distance to cartesian with matching radius', () => {
    const out = raDecDistanceToCartesian(0, 0, 10)
    expect(out.r).toBeCloseTo(logScaleDistance(10), 12)
    expect(out.x).toBeCloseTo(out.r, 12)
    expect(out.y).toBeCloseTo(0, 12)
    expect(out.z).toBeCloseTo(0, 12)
  })
})
