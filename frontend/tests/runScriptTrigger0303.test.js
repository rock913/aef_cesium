import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('0303 HOT RELOAD trigger contracts', () => {
  it('UnifiedArtifactsPanel exposes a HOT RELOAD button and emits run-code', () => {
    const s = read('../src/views/workbench/components/UnifiedArtifactsPanel.vue')
    expect(s).toMatch(/HOT RELOAD/)
    expect(s).not.toMatch(/WIND PRESET/)
    expect(s).toMatch(/defineEmits\(\[[^\]]*'run-code'[^\]]*\]\)/)
    expect(s).toMatch(/emit\('run-code'/)
  })

  it('WorkbenchApp wires @run-code and routes WGSL to executeDynamicWgsl', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toMatch(/@run-code\s*=\s*"handleRunCode"/)
    expect(s).toMatch(/function handleRunCode\(/)
    expect(s).toMatch(/executeDynamicWgsl/)
    // Guard: make sure Cesium (earth+twin) is active.
    expect(s).toMatch(/setScale\('earth'\)/)
    expect(s).toMatch(/ensureTabKind\('twin'\)/)
  })
})
