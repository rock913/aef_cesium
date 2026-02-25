import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function readAppVue() {
  const p = path.resolve(__dirname, '../src/App.vue')
  return fs.readFileSync(p, 'utf-8')
}

describe('Mobile layout & gesture isolation (TDD)', () => {
  it('makes lobby scrollable on small screens', () => {
    const s = readAppVue()
    expect(s).toMatch(/\.lobby[\s\S]*overflow-y:\s*auto/)
    expect(s).toMatch(/\.lobby[\s\S]*-webkit-overflow-scrolling:\s*touch/)
    expect(s).toMatch(/\.lobby[\s\S]*touch-action:\s*pan-y/)
  })

  it('converts ai-panel to a bottom-sheet drawer on mobile', () => {
    const s = readAppVue()
    expect(s).toMatch(/@media\s*\(max-width:\s*720px\)/)
    expect(s).toMatch(/\.ai-panel[\s\S]*bottom:\s*0/)
    expect(s).toMatch(/\.ai-panel[\s\S]*height:\s*35vh/)
    expect(s).toMatch(/\.ai-panel\.expanded[\s\S]*height:\s*85vh/)
    expect(s).toMatch(/ai-drawer-handle/)
  })

  it('stops touch/pointer events in capture phase to avoid Cesium conflicts', () => {
    const s = readAppVue()
    expect(s).toMatch(/@touchmove\.capture\.stop/)
    expect(s).toMatch(/@pointerdown\.capture\.stop/)
  })
})
