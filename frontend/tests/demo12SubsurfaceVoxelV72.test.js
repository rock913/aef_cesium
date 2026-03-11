import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('v7.2 Demo 12 subsurface voxel cloud contracts', () => {
  it('Workbench dispatches add_subsurface_model tool', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).toMatch(/tool\s*===\s*'add_subsurface_model'/)
    expect(sWorkbench).toMatch(/addSubsurfaceModel/)
  })

  it('EngineRouter addSubsurfaceModel uses PointPrimitiveCollection voxel cloud', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/async function addSubsurfaceModel\(/)
    expect(sEngine).toMatch(/new\s+Cesium\.PointPrimitiveCollection\(/)
    expect(sEngine).toMatch(/_setOverlayEntry\([^\n]*subsurfaceModel[^\n]*kind:\s*'primitive'/)
  })

  it('Overlay cleanup supports primitive removal', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/entry\.kind\s*===\s*'primitive'/)
    expect(sEngine).toMatch(/scene\?\.primitives\?\.remove\?\./)
  })
})
