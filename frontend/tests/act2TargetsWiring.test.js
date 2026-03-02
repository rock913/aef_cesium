import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Act2 target selection (TDD gate)', () => {
  it('exposes target chips and URL sync', () => {
    const s = read('../src/Act2App.vue')

    expect(s).toContain('aria-label="Act2 targets"')
    expect(s).toContain("id: 'poyang'")
    expect(s).toContain("id: 'yancheng'")
    expect(s).toContain("id: 'yangtze'")

    expect(s).toContain('function setTarget')
    expect(s).toContain('window.history.replaceState')
    expect(s).toContain("url.searchParams.set('choreo'")
  })
})
