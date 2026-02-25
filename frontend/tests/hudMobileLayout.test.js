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
    // Bottom-sheet style: collapsed and expanded heights.
    expect(s).toMatch(/\.hud-panel[\s\S]*height:\s*30vh/)
    expect(s).toMatch(/\.hud-panel\.expanded[\s\S]*height:\s*80vh/)
    expect(s).toMatch(/\.hud-panel[\s\S]*overflow-y:\s*auto/)
    // Ensure vertical scroll gestures are handled by the HUD, not the canvas.
    expect(s).toMatch(/\.hud-panel[\s\S]*touch-action:\s*pan-y/)

    // Drawer affordance exists (handle/button).
    expect(s).toMatch(/drawer-handle/)

    // Gesture isolation: events in HUD should not bubble to Cesium.
    expect(s).toMatch(/@touchmove\.stop/)
    expect(s).toMatch(/@pointerdown\.stop/)
  })
})
