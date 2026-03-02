import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Golden path (Landing → Act2) wiring', () => {
  it('hardwires free-form omni input to cinematic navigation', () => {
    const s = read('../src/Zero2xApp.vue')

    // Free-form intent should store and route to Act2 with fade.
    expect(s).toContain("sessionStorage?.setItem?.('z2x:lastIntent'")
    expect(s).toContain("reason: 'omnibar-intent'")
    expect(s).toContain("delayMs: 520")
    expect(s).toContain("buildAct2ChoreoHref('poyang')")
  })

  it('does not rely on fragile scroll auto-jump for demos', () => {
    const s = read('../src/Zero2xApp.vue')

    // No one-shot IntersectionObserver auto-navigation.
    expect(s).not.toContain('z2x:auto-act2:done')
    expect(s).not.toContain('landing-scroll-act2')
  })
})
