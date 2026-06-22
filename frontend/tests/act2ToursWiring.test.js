import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Act2 tours (recommended paths) wiring', () => {
  it('exposes recommended tours in target scene', () => {
    const s = read('../src/Act2App.vue')

    expect(s).toContain('aria-label="Recommended tours"')
    expect(s).toContain("id: 'delta-trip'")
    expect(s).toContain("id: 'coast-hop'")
    expect(s).toContain('Recommended Path')
  })

  it('plays tour via setTarget + replay (no hard reload)', () => {
    const s = read('../src/Act2App.vue')

    expect(s).toContain('function playTour')
    expect(s).toContain('setTarget(next)')
    expect(s).toContain('replay()')
    expect(s).toContain('window.history.replaceState')
  })
})
