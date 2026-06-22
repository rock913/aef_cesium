import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Catalog fetch: controls-end debounce (Stage 3)', () => {
  it('wires OrbitControls end event and uses a debounce + FOV cap', () => {
    const s = read('../src/views/workbench/engines/ThreeTwin.vue')

    // Event-driven: should schedule fetch after user stops interacting.
    expect(s).toContain("addEventListener('end'")

    // Debounce must exist (setTimeout is ok; keep implementation flexible).
    expect(s).toMatch(/CATALOG_FETCH_DEBOUNCE_MS|setTimeout\(/)

    // Avoid large-FOV requests that explode point counts.
    expect(s).toMatch(/CATALOG_FETCH_MAX_FOV_DEG|fovDeg\s*[<>]=?\s*\d+/)
  })
})
