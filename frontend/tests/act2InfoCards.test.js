import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Act2 cinematic info cards (TDD gate)', () => {
  it('renders a step-driven info card overlay', () => {
    const s = read('../src/Act2App.vue')

    expect(s).toContain('class="info"')
    expect(s).toContain(':key="activeStep"')
    expect(s).toContain('aria-live="polite"')

    // Ensure progressive reveal copy catalog exists.
    expect(s).toContain('const infoCopy')
    expect(s).toContain('CINEMATIC / 01')
    expect(s).toContain('CINEMATIC / 04')
  })

  it('fills real Poyang case copy and provides a workbench CTA', () => {
    const s = read('../src/Act2App.vue')
    expect(s).toContain('CASE / POYANG')
    expect(s).toContain('候鸟科学家助手')
    expect(s).toContain('在工作台中生成专属 Agent')
    expect(s).toContain("navigateWithFade('/workbench'")
  })

  it('keeps escape hatches visible (landing + demo)', () => {
    const s = read('../src/Act2App.vue')
    expect(s).toContain('Back to Landing')
    expect(s).toContain('Open Demo')
  })
})
