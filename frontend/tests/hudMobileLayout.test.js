import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function readHudPanel() {
  const p = path.resolve(__dirname, '../src/components/HudPanel.vue')
  return fs.readFileSync(p, 'utf-8')
}

describe('HudPanel mobile layout (TDD)', () => {
  it('provides a mobile media query and enables internal scrolling', () => {
    const s = readHudPanel()
    expect(s).toMatch(/@media\s+screen\s+and\s+\(max-width:\s*768px\)/)
    // On mobile the panel must become a bottom drawer and scroll internally.
    expect(s).toMatch(/\.hud-panel[\s\S]*bottom:\s*0/)
    expect(s).toMatch(/\.hud-panel[\s\S]*max-height:\s*60vh/)
    expect(s).toMatch(/\.hud-panel[\s\S]*overflow-y:\s*auto/)
  })
})
