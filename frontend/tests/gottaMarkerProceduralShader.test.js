import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('GOTTA marker (P0 procedural shader)', () => {
  it('avoids CanvasTexture/SpriteMaterial and uses ShaderMaterial SDF', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    // CanvasTexture sprites are prone to jaggy/texel edges at close zoom.
    // We want a procedural SDF-style marker shader.
    expect(s).toContain('GOTTA marker')
    expect(s).toContain('new THREE.ShaderMaterial')

    // Ensure we no longer rely on SpriteMaterial for GOTTA markers.
    expect(s).not.toContain('new THREE.SpriteMaterial')
  })
})
