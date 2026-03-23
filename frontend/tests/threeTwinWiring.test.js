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

    // Phase 2.5: GOTTA capture should support spline dive choreography.
    expect(s).toContain('CatmullRomCurve3')
  })

  it('matches Milestone 2 baseline scene sizes', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('100000')
    expect(s).toContain('2400')

    // Phase 2.5: redshift burst must be true radial expansion (not one-axis drift).
    expect(s).toContain('true radial expansion')
    expect(s).toContain('baseDist = length(localPos')
    expect(s).toContain('currentDist')
  })

  it('wires OneAstronomy stage2 actions (redshift + modal inpaint)', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('useAstroStore')
    expect(s).toContain('ASTRO_AGENT_ACTION_TYPES')
    expect(s).toContain('EXECUTE_REDSHIFT_PREDICTION')
    expect(s).toContain('CAPTURE_TRANSIENT_EVENT')
    expect(s).toContain('START_MODAL_INPAINT')
    expect(s).toContain('STOP_MODAL_INPAINT')
    expect(s).toContain('{ immediate: true }')

    // Phase 2.5: inpaint should accept an action payload to anchor in world-space.
    expect(s).toContain('function _startModalInpaint(payload')
    expect(s).toContain('payload?.ra')
    expect(s).toContain('_gottaLastTargetPos')

    // Astro-GIS Phase 1: layer state store should be mapped inside ThreeTwin.
    expect(s).toContain('ASTRO_GIS_LAYER_IDS')
    expect(s).toContain('astroStore.astroGis.value?.version')
  })

  it('wires OneAstronomy Demo 1 (CSST decomposition) actions', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    expect(s).toContain('DECOMPOSE_CSST_GALAXY')
    expect(s).toContain('STOP_CSST_DECOMPOSITION')
    expect(s).toContain('_startCsstDecomposition')
    expect(s).toContain('_stopCsstDecomposition')

    // CSST overlay should follow the same anti-screenshot rules (feather + vignette).
    expect(s).toContain('edgeFeather')
    expect(s).toContain('vignette')

    // CSST overlay should hard-crop into a circle (strong anti-screenshot).
    expect(s).toContain('circleMask')
    expect(s).toContain('smoothstep(0.45')

    // CSST should avoid a flat, front-facing "card" look (tilt + side-view choreography).
    expect(s).toContain('rotation.x')
    expect(s).toContain('crossVectors')
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

    // Astro-GIS Phase 1: inpaint layer opacity must be controllable.
    expect(s).toContain('u_layer_opacity')

    // Starting inpaint should collapse any redshift burst back to 0 (prevents particle-plane intersection chaos).
    expect(s).toContain('u_redshift_scale')
    expect(s).toContain('_setMacroRedshiftScale(0)')
  })

  it('supports Micro-Real-Data injection (SDSS sample) with safe fallback', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    // Macro baseline must be a sky-sphere (not the historical spiral disk).
    expect(s).toContain('MACRO_SKY_RADIUS')
    expect(s).toContain('const MACRO_SKY_RADIUS = 100')
    expect(s).not.toContain('angle = t * Math.PI * 12')

    // The dataset path is part of the public contract.
    expect(s).toContain('/data/astronomy/sdss_micro_sample.json')

    // SDSS loader must support both 2D triples and flat-array formats.
    expect(s).toContain('normalizeSdssTriples')

    // Tiny SDSS samples must not collapse the macro starfield draw-count.
    expect(s).toContain('PURE_DATA_MIN')

    // Demo 3: GOTTA transient capture uses a public mock JSON contract.
    expect(s).toContain('/data/astronomy/gotta_transient_event.json')

    // GOTTA should accept the network schema as well as the legacy single-event format.
    expect(s).toContain('targetEventId')
    expect(s).toContain('events')

    // Coordinate mapping should rely on the shared astronomy helpers.
    expect(s).toContain('coordinateMath')
    expect(s).toContain('raDecToUnitVector')

    // SDSS / GOTTA sky mapping must not flatten declination into a disk.
    expect(s).not.toContain('dir.z * radius * 0.35')
    expect(s).not.toContain('dir.z * dist * 0.35')
  })

  it('keeps macro stars readable at default camera distances', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    // Phase 2.6 (update_patch.md): macro renderer should be soft-particle points
    // so additive blending self-fuses into a cosmic web instead of "candy spheres".
    expect(s).toContain('new THREE.Points')
    expect(s).toContain('new THREE.BufferGeometry')
    expect(s).toContain("setAttribute('position'")
    expect(s).toContain("setAttribute('aRedshift'")
    expect(s).toContain('gl_PointCoord')
    expect(s).toContain('discard')
    expect(s).toContain('gl_PointSize')

    // Astro-GIS Phase 2: HiPS underlay should be present and adapter-driven.
    expect(s).toContain('HiPS Underlay')
    expect(s).toContain('initAladinLiteV3')
    expect(s).toContain('setAladinView')

    // Astro-GIS Phase 3: catalog SIMBAD overlay should be wired (backend endpoint + points material).
    expect(s).toContain('/api/astro-gis/catalog/simbad')
    expect(s).toContain('CATALOG_SIMBAD')
    expect(s).toContain('aMag')

    // Cinematic polish (update_patch.md): overlap trick + heatmap palette.
    // Big halo (size) + low base opacity, and a 3-stop palette (near/mid/far).
    expect(s).toContain('u_opacity: { value: 0.15')
    expect(s).toContain('u_size: { value: 45.0')
    expect(s).toContain('exp(-r * 5.0)')
    expect(s).toContain('colorNear')
    expect(s).toContain('colorMid')
    expect(s).toContain('colorFar')
    expect(s).toContain('smoothstep(0.0, 0.5')
    expect(s).toContain('smoothstep(0.5, 1.0')

    // Cinematic polish: dolly zoom on redshift burst (FOV pull + projection update).
    expect(s).toContain('gsap.to(camera')
    expect(s).toContain('fov: 95')
    expect(s).toContain('camera.updateProjectionMatrix()')

    // Cinematic polish: tighten bloom so filaments ignite (threshold/strength).
    expect(s).toContain('threshold: 0.4')
    expect(s).toContain('strength: 2.2')
  })
})
