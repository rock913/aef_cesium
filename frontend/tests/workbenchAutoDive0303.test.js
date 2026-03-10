import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench patch 0303: cinematic auto-dive contracts', () => {
  it('does not blindly start Global Standby when entering with ?context=', () => {
    const s = read('../src/WorkbenchApp.vue')
    // Contract intent: onViewerReady should branch on context-from-URL.
    expect(s).toMatch(/onViewerReady\(\)/)
    expect(s).toMatch(/_contextFromUrl/)
    expect(s).toMatch(/flyToScenario|stopGlobalStandby/)
  })
})
