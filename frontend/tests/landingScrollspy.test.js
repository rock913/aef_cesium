import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Landing scrollytelling progress (TDD gate)', () => {
  it('implements a visible scrollspy progress nav', () => {
    const s = read('../src/Zero2xApp.vue')

    // update_patch_0303: remove traditional right-side pills; keep scrollspy wiring
    // but use a subtle scroll hint to preserve the cinematic trailer feel.
    expect(s).not.toContain('aria-label="Story progress"')
    expect(s).toContain('scroll-hint')
    expect(s).toContain('mouse-icon')
    expect(s).toContain('IntersectionObserver')
    expect(s).toContain('activeAct')
    expect(s).toContain('data-act-id="act-2"')
    expect(s).toContain('data-act-id="act-5"')
  })

  it('reduces prominent demo entry on hero (demo link is not in primary actions)', () => {
    const s = read('../src/Zero2xApp.vue')

    // Keep /demo available but de-emphasized (footer link is OK).
    expect(s).not.toContain('Open Demo</a>')
    expect(s).toContain('href="/demo"')
  })
})
