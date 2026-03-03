import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Golden Path wiring (TDD gate)', () => {
  it('Landing stores scenario context and teleports to Workbench on selection', () => {
    const s = read('../src/Zero2xApp.vue')
    expect(s).toContain("sessionStorage?.setItem?.('z2x:lastContext'")
    expect(s).toContain('/workbench?context=')
    expect(s).toMatch(/window\.location\.(href|assign)\s*=|window\.location\.(assign|replace)\(/)

    // Avoid demo-fragile auto-jump behavior.
    expect(s).not.toContain('z2x:auto-act2:done')
    expect(s).not.toContain('landing-scroll-act2')
  })

  it('Act2 has a summary CTA to /workbench with cinematic navigation', () => {
    const s = read('../src/Act2App.vue')
    expect(s).toContain('在工作台中生成专属 Agent')
    expect(s).toContain("navigateWithFade('/workbench'")
  })

  it('Workbench auto-plays a demo and avoids placeholder UI copy', () => {
    const s = read('../src/WorkbenchApp.vue')
    expect(s).toContain("setTimeout(() => runStub(),")
    expect(s).toContain("sessionStorage?.getItem?.('z2x:lastContext'")
    expect(s).not.toMatch(/Placeholder/i)
  })
})
