import { describe, expect, it, vi } from 'vitest'
import { executeQuantumDive } from '../src/views/workbench/engines/quantumDive.js'

describe('executeQuantumDive (wormhole transition)', () => {
  it('animates camera fov, switches scene at peak, then settles', () => {
    const camera = {
      fov: 60,
      position: { set: vi.fn() },
      updateProjectionMatrix: vi.fn(),
    }

    const calls = []
    const gsap = {
      to: vi.fn((target, vars) => {
        calls.push({ target, vars })
        return { target, vars }
      }),
    }

    const onSwitchScene = vi.fn()

    executeQuantumDive({
      camera,
      onSwitchScene,
      gsap,
      peakFov: 150,
      settleFov: 60,
      microPose: { x: 0, y: 0, z: 5 },
      settleZ: 40,
      inhaleDuration: 1.2,
      exhaleDuration: 1.5,
    })

    expect(gsap.to).toHaveBeenCalled()
    expect(calls[0].vars.fov).toBe(150)

    // Simulate peak completion
    calls[0].vars.onComplete()

    expect(onSwitchScene).toHaveBeenCalledTimes(1)
    expect(camera.position.set).toHaveBeenCalledWith(0, 0, 5)

    expect(calls[1].vars.fov).toBe(60)
    expect(calls[1].vars.z).toBe(40)
  })
})
