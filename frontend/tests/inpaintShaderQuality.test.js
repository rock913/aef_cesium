import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Inpaint shader quality (P0 anti-alias + grain)', () => {
  it('uses smoothstep feathering, fwidth AA, grain and vignette', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    // Core: must feather the scan boundary (no hard if/else edge).
    expect(s).toContain('smoothstep(u_radius')

    // Anti-alias: prefer analytic AA via fwidth.
    expect(s).toContain('fwidth')

    // Film grain: hides texture mosaic artifacts at close zoom.
    expect(s).toContain('grain')
    expect(s).toContain('hash21')

    // Must keep the anti-screenshot soft vignette.
    expect(s).toContain('vignette')
  })
})
