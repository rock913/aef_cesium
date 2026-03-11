import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('v7.2 Demo 6 Talatan PV contracts', () => {
  it('Backend tool is dispatched: Workbench handles add_cesium_extruded_polygons', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).toMatch(/tool\s*===\s*'add_cesium_extruded_polygons'/)
    expect(sWorkbench).toMatch(/addExtrudedPolygons/)
  })

  it('EngineRouter supports extruded polygons rendering', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/async function addExtrudedPolygons\(/)
    expect(sEngine).toMatch(/GeoJsonDataSource\.load/)
    expect(sEngine).toMatch(/extrudedHeight/)
  })

  it('Artifacts pipeline understands add_cesium_vector', () => {
    const sArtifacts = read('../src/utils/copilotArtifacts.js')
    expect(sArtifacts).toMatch(/tool\s*===\s*'add_cesium_vector'/)
    expect(sArtifacts).toMatch(/ai-vector/)
  })
})
