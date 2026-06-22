import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('v7.2 Demo 10 NYC bivariate overlay contracts', () => {
  it('EngineRouter implements bivariate grid overlay renderer', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/async function renderBivariateGridOverlay\(/)
    expect(sEngine).toMatch(/CustomDataSource/)
    expect(sEngine).toMatch(/Rectangle\.fromDegrees/)
    expect(sEngine).toMatch(/_RUNTIME_KEYS\.bivariate/)
  })

  it('EngineScaleRouter exposes renderBivariateGridOverlay passthrough', () => {
    const sScale = read('../src/views/workbench/EngineScaleRouter.vue')
    expect(sScale).toMatch(/async function renderBivariateGridOverlay\(/)
    expect(sScale).toMatch(/renderBivariateGridOverlay/)
  })

  it('Workbench dispatches render_bivariate_map tool calls to engine overlay', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).toMatch(/tool\s*===\s*'render_bivariate_map'/)
    expect(sWorkbench).toMatch(/renderBivariateGridOverlay/)
  })
})
