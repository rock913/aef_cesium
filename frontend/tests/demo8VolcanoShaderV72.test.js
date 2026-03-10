import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('v7.2 Demo 8 volcano custom shader contracts', () => {
  it('EngineRouter implements applyCustomShader with a demo-safe fallback', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/async function applyCustomShader\(/)
    // Prefer real Cesium.CustomShader when available.
    expect(sEngine).toMatch(/CustomShader/)
    // Fallback should still render without external assets.
    expect(sEngine).toMatch(/ellipsoid/)
    expect(sEngine).toMatch(/CallbackProperty/)
  })

  it('EngineScaleRouter exposes applyCustomShader passthrough', () => {
    const sScale = read('../src/views/workbench/EngineScaleRouter.vue')
    expect(sScale).toMatch(/async function applyCustomShader\(/)
    expect(sScale).toMatch(/applyCustomShader/)
  })

  it('Workbench dispatches apply_custom_shader and consumes generate_cesium_custom_shader results', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).toMatch(/tool\s*===\s*'apply_custom_shader'/)
    expect(sWorkbench).toMatch(/tool\s*===\s*'generate_cesium_custom_shader'/)
    expect(sWorkbench).toMatch(/code\.value\s*=\s*codeArg/)
  })
})
