import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench v7.1 Global Standby + Lab persistence', () => {
  it('defaults to Global Standby, but supports one-shot auto-fly for deep-links', () => {
    const s = read('../src/WorkbenchApp.vue')

    // viewer-ready should still support standby
    expect(s).toMatch(/function onViewerReady\(\)[\s\S]*startGlobalStandby/)

    // but also allow conditional fly when a deep-link requested it
    expect(s).toMatch(/pendingAutoFly/)
    expect(s).toMatch(/function onViewerReady\(\)[\s\S]*flyToScenario/)
  })

  it('does not force Theater mode after execute', () => {
    const s = read('../src/WorkbenchApp.vue')

    // Lab mode should remain stable unless user explicitly toggles F11/button.
    expect(s).not.toMatch(/finally\s*\{[\s\S]*setMode\(['"]theater['"]\)/)
  })

  it('keeps workbench quiet unless autoplay is requested', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toContain('const _autoplayFromUrl')
    expect(s).toMatch(/if\s*\(_autoplayFromUrl\s*\|\|\s*_contextFromUrl\)[\s\S]*setTimeout\(\(\)\s*=>\s*_focusScenario\(/)
  })

  it('uses backend-provided height/duration for fly_to', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toMatch(/tool\s*===\s*'camera_fly_to'\s*\|\|\s*tool\s*===\s*'fly_to'/)
    expect(s).toMatch(/Number\(args\?\.height\)/)
    expect(s).toMatch(/Number\(args\?\.duration_s\)/)
  })
})
