import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Golden path (Landing → Act2) wiring', () => {
  it('teleports Omni-Bar scenario selection directly to /workbench', () => {
    const s = read('../src/Zero2xApp.vue')

    // Click-to-select command palette should store context and jump straight to the heavy workbench.
    expect(s).toContain("sessionStorage?.setItem?.('z2x:lastContext'")
    expect(s).toContain('/workbench?context=')
    expect(s).toMatch(/window\.location\.(href|assign)\s*=|window\.location\.(assign|replace)\(/)
  })

  it('does not rely on fragile scroll auto-jump for demos', () => {
    const s = read('../src/Zero2xApp.vue')

    // No one-shot IntersectionObserver auto-navigation.
    expect(s).not.toContain('z2x:auto-act2:done')
    expect(s).not.toContain('landing-scroll-act2')
  })
})
