import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench demo copy (no placeholders)', () => {
  it('removes placeholder wording from the visible demo flow', () => {
    const s = read('../src/WorkbenchApp.vue')

    expect(s).not.toContain('(placeholder)')
    expect(s).not.toContain('Placeholder')
    expect(s).toContain('Agent (demo):')
    expect(s).toContain("sessionStorage?.getItem?.('z2x:lastContext')")

    // zero2x_v6: full-screen twin with floating glass HUD panels.
    expect(s).toMatch(/pointer-events:\s*none/)
    expect(s).toMatch(/backdrop-filter:\s*blur\(/)
  })
})
