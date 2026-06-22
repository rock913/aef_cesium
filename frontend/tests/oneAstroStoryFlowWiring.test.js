import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(rel) {
  return fs.readFileSync(path.resolve(__dirname, rel), 'utf-8')
}

describe('OneAstronomy Story Flow wiring (Phase 2.5)', () => {
  it('exposes a one-click preset that dispatches the story action', () => {
    const s = read('../src/WorkbenchApp.vue')

    expect(s).toContain("id: 'demo:oneastro_story'")
    expect(s).toContain('Story Flow (4 Acts)')
    expect(s).toContain('EXECUTE_ONEASTRO_STORY_FLOW')
  })

  it('declares story flow action types in astroStore', () => {
    const s = read('../src/stores/astroStore.js')

    expect(s).toContain('EXECUTE_ONEASTRO_STORY_FLOW')
    expect(s).toContain('STOP_ONEASTRO_STORY_FLOW')
  })

  it('runs the 4-act sequence in order in ThreeTwin', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    const iStory = s.indexOf('async function _executeOneAstroStoryFlow')
    expect(iStory).toBeGreaterThan(-1)

    const iCsst = s.indexOf('_startCsstDecomposition', iStory)
    const iStopCsst = s.indexOf('_stopCsstDecomposition', iCsst)
    const iRedshift = s.indexOf('_executeRedshiftBurst', iStopCsst)
    const iGotta = s.indexOf('_captureTransientEvent', iRedshift)
    const iInpaint = s.indexOf('_startModalInpaint', iGotta)

    expect(iCsst).toBeGreaterThan(-1)
    expect(iStopCsst).toBeGreaterThan(iCsst)
    expect(iRedshift).toBeGreaterThan(iStopCsst)
    expect(iGotta).toBeGreaterThan(iRedshift)
    expect(iInpaint).toBeGreaterThan(iGotta)
  })
})
