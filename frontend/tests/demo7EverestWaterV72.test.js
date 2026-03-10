import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('v7.2 Demo 7 Everest water/flood contracts', () => {
  it('EngineRouter exposes a resource-free animated water polygon helper', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/addWaterPolygon/)
    expect(sEngine).toMatch(/CallbackProperty/)
    expect(sEngine).toMatch(/positions_degrees/)
  })

  it('Workbench dispatches add_cesium_water_polygon tool calls', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).toMatch(/tool\s*===\s*'add_cesium_water_polygon'/)
  })
})
