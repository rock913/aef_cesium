import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench v7.2: Swipe + contextual timeline contracts', () => {
  it('removes EXECUTE ON TWIN and does not wire TimelineHUD execute', () => {
    const sHud = read('../src/views/workbench/components/TimelineHUD.vue')
    expect(sHud).not.toContain('EXECUTE ON TWIN')
    expect(sHud).not.toContain("defineEmits(['execute'])")
    // Patch 0303: TimelineHUD must be controlled (no internal timers).
    expect(sHud).not.toMatch(/setInterval\(/)
    expect(sHud).not.toMatch(/clearInterval\(/)

    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).not.toContain('<TimelineHUD @execute')
  })

  it('makes timeline contextual (only when context indicates time)', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    // Patch 0303: contextual + data-ready gating.
    expect(sWorkbench).toMatch(/currentContextHasTime|showTimeline|hasTime/)
    expect(sWorkbench).toMatch(/isTimeSeriesDataReady/)
  })

  it('adds Swipe HUD and Cesium split plumbing hooks', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    expect(sWorkbench).toMatch(/Swipe|swipe/i)
    expect(sWorkbench).toMatch(/const\s+swipeEnabled\s*=\s*ref\(false\)/)

    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/splitPosition/)
    expect(sEngine).toMatch(/ImagerySplitDirection/)
    expect(sEngine).toMatch(/setSwipeMode|set_swipe/i)
  })

  it('exposes Swipe left/right layer selectors (Left non-AI, Right AI-only)', () => {
    const sPanel = read('../src/views/workbench/components/UnifiedArtifactsPanel.vue')
    expect(sPanel).toContain('SWIPE COMPARE')
    expect(sPanel).toMatch(/Left/)
    expect(sPanel).toMatch(/Right/)

    // Contract: right side is AI-only (ai-imagery or ai-*).
    expect(sPanel).toMatch(/ai-imagery|startsWith\('ai-'\)/)
  })

  it('moves Swipe toggle out of top-nav into Layers panel (patch 0303)', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')
    // No dedicated top-right "Swipe" action button.
    expect(sWorkbench).not.toMatch(/@click=\"toggleSwipe\"/)

    const sPanel = read('../src/views/workbench/components/UnifiedArtifactsPanel.vue')
    // Panel must provide a view-mode controller that can enable Swipe.
    expect(sPanel).toMatch(/View Mode|VIEW MODE|Overlay|SWIPE MODE|Swipe Mode|Overlay Mode/)
    expect(sPanel).toMatch(/swipeEnabled|update:swipeEnabled|swipe-enabled/)
  })

  it('decouples free chat from demo stub (latest patch 0303 feedback)', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')

    // Free input should apply backend events and NOT run the demo script.
    expect(sWorkbench).toMatch(/function onCopilotSubmit\(text\)/)
    expect(sWorkbench).not.toMatch(/function onCopilotSubmit\(text\)[\s\S]*runExecute\(\)/)

    // Preset/demo path may still run a deterministic script.
    expect(sWorkbench).toMatch(/function applyPreset\(preset\)[\s\S]*runStub\(\)/)
  })

  it('hardens Cesium interactions: disable LEFT_DOUBLE_CLICK tracking + vector swipe hook', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')

    // Avoid the "double-click boundary -> camera disaster" in demos.
    expect(sEngine).toMatch(/LEFT_DOUBLE_CLICK/)
    expect(sEngine).toMatch(/removeInputAction/)

    // Vector overlays (GeoJSON/entities) must at least have a swipe-cut hook.
    // Either true clipping planes (when supported) or a screen-space fallback.
    expect(sEngine).toMatch(/ClippingPlaneCollection|wgs84ToWindowCoordinates|SceneTransforms/)
  })
})
