import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function readCesiumViewerVue() {
  const p = path.resolve(__dirname, '../src/components/CesiumViewer.vue')
  return fs.readFileSync(p, 'utf-8')
}

describe('Cesium basemap production guard', () => {
  it('supports disabling default imagery via env toggle', () => {
    const s = readCesiumViewerVue()
    expect(s).toContain('VITE_DISABLE_DEFAULT_IMAGERY')
    // Ensure we explicitly set baseLayer when the toggle is enabled.
    expect(s).toMatch(/disableDefaultImagery[\s\S]*\?\s*\{\s*baseLayer:/)
  })
})
