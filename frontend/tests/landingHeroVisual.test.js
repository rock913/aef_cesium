import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Landing hero visual pack (Issue #14, TDD gate)', () => {
  it('wires a dedicated HeroVisual layer into act-1 hero', () => {
    const s = read('../src/Zero2xApp.vue')
    expect(s).toContain("import HeroVisual")
    expect(s).toContain("./components/HeroVisual.vue")
    expect(s).toContain('<HeroVisual')
  })

  it('HeroVisual is lightweight: dynamic-imports three and cleans up on unmount', () => {
    const s = read('../src/components/HeroVisual.vue')
    expect(s).toContain("await import('three')")
    expect(s).toContain('onUnmounted')
    expect(s).toContain('renderer.dispose')
    expect(s).toContain('cancelAnimationFrame')

    // Design drop-in assets must remain wired.
    expect(s).toContain('stardust_bg.webm')
    expect(s).toContain('glow_sphere.webm')
  })

  it('documents asset drop-in paths for design iteration', () => {
    const heroReadme = path.resolve(__dirname, '../public/zero2x/hero/README.md')
    const uiReadme = path.resolve(__dirname, '../public/zero2x/ui/README.md')

    expect(fs.existsSync(heroReadme)).toBe(true)
    expect(fs.existsSync(uiReadme)).toBe(true)

    const s = fs.readFileSync(heroReadme, 'utf-8')
    expect(s).toContain('Issue #14')
    expect(s).toContain('stardust_bg.webm')
    expect(s).toContain('glow_sphere.webm')
  })
})
