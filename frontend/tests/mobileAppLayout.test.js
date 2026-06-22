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
    expect(s).toMatch(/\.ai-panel[\s\S]*height:\s*50vh/)
    expect(s).toMatch(/\.ai-panel\.expanded[\s\S]*height:\s*85vh/)
    expect(s).toMatch(/ai-drawer-handle/)
  })

  it('hides CENTER debug coords on mobile', () => {
    const s = readAppVue()
    expect(s).toMatch(/@media\s*\(max-width:\s*720px\)[\s\S]*\.debug-center[\s\S]*display:\s*none/)
  })

  it('hides Hold Compare control on desktop too', () => {
    const s = readAppVue()
    const holdRuleIdx = s.indexOf('.ai-actions .ai-btn-hold')
    const mediaIdx = s.indexOf('@media (max-width: 720px)')
    expect(holdRuleIdx).toBeGreaterThan(-1)
    expect(mediaIdx).toBeGreaterThan(-1)
    expect(holdRuleIdx).toBeLessThan(mediaIdx)
    expect(s).toMatch(/\.ai-actions\s+\.ai-btn-hold[\s\S]*display:\s*none/)
  })

  it('hides compare controls on mobile (keep only AI Layer)', () => {
    const s = readAppVue()
    expect(s).toMatch(/\.ai-actions\s+\.ai-btn-swipe[\s\S]*display:\s*none/)
    expect(s).toMatch(/\.ai-actions\s+\.ai-btn-hold[\s\S]*display:\s*none/)
  })

  it('stops touch/pointer events in capture phase to avoid Cesium conflicts', () => {
    const s = readAppVue()
    expect(s).toMatch(/@touchmove\.capture\.stop/)
    expect(s).toMatch(/@pointerdown\.capture\.stop/)
  })
})
