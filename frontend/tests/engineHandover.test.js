import { describe, it, expect, vi } from 'vitest'
import { syncCesiumToThreeCamera } from '../src/utils/astronomy/engineHandover.js'

describe('engineHandover', () => {
  it('syncs direction/up into a Three-like camera', () => {
    const cesiumCamera = {
      directionWC: { x: 1, y: 0, z: 0 },
      upWC: { x: 0, y: 0, z: 1 },
    }

    const upSet = vi.fn()
    const lookAt = vi.fn()

    const threeCamera = {
      position: { x: 0, y: 0, z: 10 },
      up: { set: upSet },
      lookAt,
    }

    const out = syncCesiumToThreeCamera(cesiumCamera, threeCamera)

    expect(upSet).toHaveBeenCalledWith(0, 0, 1)
    expect(lookAt).toHaveBeenCalledWith(1, 0, 10)
    expect(out.raDeg).toBeCloseTo(0, 6)
    expect(out.decDeg).toBeCloseTo(0, 6)
  })

  it('can force camera origin', () => {
    const cesiumCamera = {
      directionWC: { x: 0, y: 1, z: 0 },
      upWC: { x: 0, y: 0, z: 1 },
    }

    const threeCamera = {
      position: { x: 5, y: 6, z: 7 },
      up: { set: vi.fn() },
      lookAt: vi.fn(),
    }

    syncCesiumToThreeCamera(cesiumCamera, threeCamera, { forceOrigin: true })
    expect(threeCamera.position).toEqual({ x: 0, y: 0, z: 0 })
  })
})
