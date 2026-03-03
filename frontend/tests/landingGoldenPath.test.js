import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Golden path (Landing → Act2) wiring', () => {
  it('binds scenario selection to Act5 launchpad scroll', () => {
    const s = read('../src/Zero2xApp.vue')

    // Click-to-select command palette should store context and scroll to Act5.
    expect(s).toContain("sessionStorage?.setItem?.('z2x:lastContext'")
    expect(s).toContain("document.getElementById('act-5')")
      expect(s).toContain('scrollIntoView({ behavior: \'smooth\' })')
    expect(s).toContain('setTimeout')
    expect(s).toContain('150')
  })

  it('does not rely on fragile scroll auto-jump for demos', () => {
    const s = read('../src/Zero2xApp.vue')

    // No one-shot IntersectionObserver auto-navigation.
    expect(s).not.toContain('z2x:auto-act2:done')
    expect(s).not.toContain('landing-scroll-act2')
  })
})
