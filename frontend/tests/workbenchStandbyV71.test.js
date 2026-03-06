import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench v7.1 Global Standby + Lab persistence', () => {
  it('does not auto-fly to scenario on viewer-ready', () => {
    const s = read('../src/WorkbenchApp.vue')

    // viewer-ready should enter standby, not jump to local camera
    expect(s).toMatch(/function onViewerReady\(\)[\s\S]*startGlobalStandby/)
    expect(s).not.toMatch(/function onViewerReady\(\)[\s\S]*_flyToScenario\(\)/)
  })

  it('does not force Theater mode after execute', () => {
    const s = read('../src/WorkbenchApp.vue')

    // Lab mode should remain stable unless user explicitly toggles F11/button.
    expect(s).not.toMatch(/finally\s*\{[\s\S]*setMode\(['"]theater['"]\)/)
  })
})
