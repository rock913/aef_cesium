import { describe, expect, it, vi } from 'vitest'
import { createBloomPipeline, updateBloomParams } from '../src/views/workbench/engines/threePostprocessing.js'

describe('threePostprocessing (bloom pipeline)', () => {
  it('wires composer, render pass, and bloom pass', () => {
    function EffectComposer(renderer) {
      this.renderer = renderer
      this.addPass = vi.fn()
      this.setSize = vi.fn()
    }

    function RenderPass(scene, camera) {
      this.scene = scene
      this.camera = camera
      this.kind = 'render'
    }

    function UnrealBloomPass(vec2, strength, radius, threshold) {
      this.size = vec2
      this.kind = 'bloom'
      this.strength = strength
      this.radius = radius
      this.threshold = threshold
      this.dispose = vi.fn()
    }

    function Vector2(w, h) {
      this.w = w
      this.h = h
    }

    const renderer = {}
    const scene = {}
    const camera = {}

    const res = createBloomPipeline({
      renderer,
      scene,
      camera,
      size: { width: 800, height: 600 },
      strength: 1.2,
      threshold: 0.75,
      radius: 0.1,
      classes: { EffectComposer, RenderPass, UnrealBloomPass, Vector2 },
    })

    expect(res.composer).toBeTruthy()
    expect(res.renderPass).toBeTruthy()
    expect(res.bloomPass).toBeTruthy()
    expect(res.bloomPass.strength).toBe(1.2)
    expect(res.bloomPass.threshold).toBe(0.75)
    expect(res.bloomPass.radius).toBe(0.1)
  })

  it('updates bloom params safely', () => {
    const bloomPass = { strength: 1, threshold: 0.2, radius: 0.0 }
    updateBloomParams(bloomPass, { strength: 2, threshold: 0.8, radius: 0.3 })
    expect(bloomPass.strength).toBe(2)
    expect(bloomPass.threshold).toBe(0.8)
    expect(bloomPass.radius).toBe(0.3)
  })
})
