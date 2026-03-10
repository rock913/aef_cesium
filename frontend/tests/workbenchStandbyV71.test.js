import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench v7.1 Global Standby + Lab persistence', () => {
  it('enters standby on viewer-ready; only auto-dives when context is present', () => {
    const s = read('../src/WorkbenchApp.vue')

    // viewer-ready should enter standby, not jump to local camera
    expect(s).toMatch(/function onViewerReady\(\)[\s\S]*startGlobalStandby/)

    // Patch 0303: allow a conditional auto-dive when entering with ?context=.
    expect(s).toMatch(
      /function onViewerReady\(\)[\s\S]*const hasContextFromUrl[\s\S]*if\s*\(hasContextFromUrl[\s\S]*_flyToScenario\(\)/
    )

    // Must not unconditionally dive (i.e., call before the context gate).
    expect(s).not.toMatch(
      /function onViewerReady\(\)[\s\S]*_flyToScenario\(\)[\s\S]*if\s*\(hasContextFromUrl/
    )
  })

  it('does not force Theater mode after execute', () => {
    const s = read('../src/WorkbenchApp.vue')

    // Lab mode should remain stable unless user explicitly toggles F11/button.
    expect(s).not.toMatch(/finally\s*\{[\s\S]*setMode\(['"]theater['"]\)/)
  })

  it('keeps workbench quiet unless autoplay is requested', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toContain('const _autoplayFromUrl')
    expect(s).toMatch(/if\s*\(_autoplayFromUrl\s*\|\|\s*_contextFromUrl\)[\s\S]*setTimeout\(\(\)\s*=>\s*runStub\(\),\s*220\)/)
  })

  it('uses backend-provided height/duration for fly_to', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toMatch(/tool\s*===\s*'camera_fly_to'\s*\|\|\s*tool\s*===\s*'fly_to'/)
    expect(s).toMatch(/Number\(args\?\.height\)/)
    expect(s).toMatch(/Number\(args\?\.duration_s\)/)
  })
})
