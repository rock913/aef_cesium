import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Act2 scrollytelling wiring (TDD gate)', () => {
  it('contains scroll sections with step markers', () => {
    const s = read('../src/Act2App.vue')
    expect(s).toContain('data-act2-step="space"')
    expect(s).toContain('data-act2-step="earth"')
    expect(s).toContain('data-act2-step="target"')
    expect(s).toContain('data-act2-step="summary"')
  })

  it('wires IntersectionObserver to applyAct2Step', () => {
    const s = read('../src/Act2App.vue')
    expect(s).toContain('IntersectionObserver')
    expect(s).toContain("from './utils/act2Timeline.js'")
    expect(s).toContain('applyAct2Step')
    expect(s).toContain('pickDominantAct2Entry')
  })
})
