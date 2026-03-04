import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench v7.x layout (glass + flex skeleton)', () => {
  it('uses a hud-layer overlay skeleton instead of floating panels', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toContain('class="workbench-root')
    expect(s).toContain('class="hud-layer')
    expect(s).toContain('pointer-events-none')
  })

  it('places LayerTree inside the right armor with the editor', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toContain('class="right-armor')
    expect(s).toContain('<LayerTree')
    expect(s).toContain('<MonacoLazyEditor')
  })

  it('LayerTree renders scale-conditional sections (earth/macro/micro)', () => {
    const s = read('../src/views/workbench/components/LayerTree.vue')
    expect(s).toContain("v-if=\"currentScale === 'earth'\"")
    expect(s).toContain("v-if=\"currentScale === 'macro'\"")
    expect(s).toContain("v-if=\"currentScale === 'micro'\"")
  })
})
