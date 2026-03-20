import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('ThreeTwin wiring (v7 dispose gate)', () => {
  it('marks raw objects and calls dispose gate on unmount', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('markRaw')
    expect(s).toContain('onBeforeUnmount')
    expect(s).toContain('disposeThreeEngine')
  })

  it('includes bloom postprocessing and quantum dive transition', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('UnrealBloomPass')
    expect(s).toContain('EffectComposer')
    expect(s).toContain('executeQuantumDive')
    expect(s).toContain("from 'gsap'")
  })

  it('matches Milestone 2 baseline scene sizes', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('100000')
    expect(s).toContain('2400')
  })

  it('wires OneAstronomy stage2 actions (redshift + modal inpaint)', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('useAstroStore')
    expect(s).toContain('ASTRO_AGENT_ACTION_TYPES')
    expect(s).toContain('EXECUTE_REDSHIFT_PREDICTION')
    expect(s).toContain('START_MODAL_INPAINT')
    expect(s).toContain('STOP_MODAL_INPAINT')
    expect(s).toContain('{ immediate: true }')
  })

  it('enforces Scene Authority 2.0 for modal inpaint (no occlusion, no screenshot edge)', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    // Inpaint must be additive + no depth test/write, and placed in front of macro content.
    expect(s).toContain('AdditiveBlending')
    expect(s).toContain('depthTest: false')
    expect(s).toContain('depthWrite: false')
    expect(s).toContain('.position.set(0, 0, 15)')

    // Shader must include edge feather / vignette to avoid a rectangular billboard boundary.
    expect(s).toContain('edgeFeather')
    expect(s).toContain('vignette')

    // Starting inpaint should collapse any redshift burst back to 0 (prevents particle-plane intersection chaos).
    expect(s).toContain('u_redshift_scale')
    expect(s).toContain('_setMacroRedshiftScale(0)')
  })
})
