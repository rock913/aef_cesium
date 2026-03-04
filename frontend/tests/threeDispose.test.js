import { describe, expect, it, vi } from 'vitest'
import { disposeThreeEngine } from '../src/views/workbench/engines/threeDispose.js'

describe('disposeThreeEngine (Dispose Gate)', () => {
  it('cancels RAF and hard-disposes renderer + scene resources', () => {
    const geomDispose = vi.fn()
    const matDispose = vi.fn()
    const mat2Dispose = vi.fn()

    const objectA = {
      geometry: { dispose: geomDispose },
      material: [{ dispose: matDispose }, { dispose: mat2Dispose }],
    }

    const scene = {
      traverse(cb) {
        cb(objectA)
      },
    }

    const renderer = {
      dispose: vi.fn(),
      forceContextLoss: vi.fn(),
      domElement: { remove: vi.fn() },
    }

    const controls = { dispose: vi.fn() }
    const cancel = vi.fn()

    disposeThreeEngine({
      renderer,
      controls,
      scenes: [scene],
      animationId: 123,
      cancelAnimationFrameFn: cancel,
    })

    expect(cancel).toHaveBeenCalledWith(123)
    expect(geomDispose).toHaveBeenCalled()
    expect(matDispose).toHaveBeenCalled()
    expect(mat2Dispose).toHaveBeenCalled()
    expect(controls.dispose).toHaveBeenCalled()
    expect(renderer.dispose).toHaveBeenCalled()
    expect(renderer.forceContextLoss).toHaveBeenCalled()
    expect(renderer.domElement.remove).toHaveBeenCalled()
  })
})
