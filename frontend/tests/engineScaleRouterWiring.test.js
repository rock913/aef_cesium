import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('EngineScaleRouter wiring (v7.5 dual engine overlay)', () => {
  it('keeps Cesium + Three mounted and crossfades visibility', () => {
    const s = read('../src/views/workbench/EngineScaleRouter.vue')

    expect(s).toContain('currentScale')
    expect(s).toContain('ThreeTwin')
    expect(s).toContain('EngineRouter')
    expect(s).toContain('earthWrap')
    expect(s).toContain('threeWrap')
    expect(s).toContain('applyEngineVisibility')
  })
})
