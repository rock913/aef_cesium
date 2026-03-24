import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Earth→Sky auto handover wiring (P0 one-shot)', () => {
  it('watches Cesium camera height and switches scale to macro', () => {
    const s = read('../src/views/workbench/EngineScaleRouter.vue')

    // Must observe Cesium camera motion (changed event) so it can react during zoom.
    expect(s).toContain('camera.changed')

    // Must switch the global scale into macro when threshold is crossed.
    expect(s).toContain("setScale('macro')")

    // Configurable threshold (fallback ok), but must be wired through env.
    expect(s).toContain('VITE_EARTH_TO_SKY_HANDOVER_HEIGHT_KM')
  })
})
