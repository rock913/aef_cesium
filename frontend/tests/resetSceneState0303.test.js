import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('0303 stability contracts: resetSceneState', () => {
  it('EngineRouter defines resetSceneState and calls it on scenario changes', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/function\s+resetSceneState\(/)
    expect(sEngine).toMatch(/watch\(\s*[\s\S]*\(\)\s*=>\s*props\.scenario\?\.id[\s\S]*resetSceneState\(\)/)
  })

  it('resetSceneState cancels in-flight loads and stops WebGPU/subsurface', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/applyToken\.value\s*\+=\s*1/)
    expect(sEngine).toMatch(/destroyWebGpuSandbox\(\)/)
    expect(sEngine).toMatch(/disableSubsurfaceMode\(\)/)
  })
})
