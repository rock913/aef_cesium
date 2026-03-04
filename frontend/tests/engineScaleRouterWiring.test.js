import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('EngineScaleRouter wiring (v7 mutual exclusivity)', () => {
  it('uses v-if/v-else mutual mount between Cesium and Three', () => {
    const s = read('../src/views/workbench/EngineScaleRouter.vue')

    expect(s).toContain("currentScale")
    expect(s).toContain("v-if=\"isEarth\"")
    expect(s).toContain("v-else")
    expect(s).toContain('ThreeTwin')
    expect(s).toContain('EngineRouter')
  })
})
