import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Demo vs Act2 boundary', () => {
  it('redirects /demo?choreo=... to /act2 (narrative route)', () => {
    const s = read('../src/App.vue')

    // Boundary intent: demo is tool/validation; narrative lives in /act2.
    expect(s).toContain('buildAct2ChoreoHref')
    expect(s).toContain('getChoreoFromSearch')
    expect(s).toContain("window.location.replace")
    expect(s).toContain('buildAct2ChoreoHref(name)')
  })

  it('does not run choreography inside demo app', () => {
    const s = read('../src/App.vue')

    // Ensure we don't regress into demo-side choreography execution.
    expect(s).not.toContain('runChoreo')
    expect(s).not.toContain('activeChoreo')
    expect(s).not.toContain('choreoHasRun')
  })
})
