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
    expect(sEngine).toMatch(/SplitDirection|ImagerySplitDirection/)
    expect(sEngine).toMatch(/setSwipeMode|set_swipe/i)
  })

  it('makes Swipe right-only with no layer selectors (left basemap stays clean)', () => {
    const sPanel = read('../src/views/workbench/components/UnifiedArtifactsPanel.vue')
    // The legacy Left/Right compare UI must be removed.
    expect(sPanel).not.toContain('SWIPE COMPARE')
    expect(sPanel).not.toMatch(/\bLeft\b/)

    // Patch 0303: no per-side selectors; swipe is a spatial state.
    expect(sPanel).not.toMatch(/\bRight\b/)
    expect(sPanel).not.toMatch(/swipeRightLayerId|swipe-right-layer-id/i)
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

  it('renders free-chat text robustly (resp.reply/text fallback before events.final)', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')

    // Patch update: avoid blank output when backend does not emit events.final.
    expect(sWorkbench).toMatch(/resp\?\.(reply|text)/)

    // Still support events.final as a fallback.
    expect(sWorkbench).toMatch(/e\.type\s*===\s*'final'|type\s*===\s*'final'/)
  })

  it('loads layers concurrently on scene switch (Promise.allSettled task pool)', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')
    expect(sEngine).toMatch(/Promise\.allSettled\(/)
    expect(sEngine).toMatch(/loadTasks|tasks|allSettled/)
  })

  it('auto-flyTo on scenario change (even if prompt emits no fly_to)', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')

    // There must be a watcher that reacts to scenario.id changes and forces a flyToScenario.
    expect(sWorkbench).toMatch(/watch\([\s\S]*\(\)\s*=>\s*scenario\.value\?\.id[\s\S]*flyToScenario/s)
    expect(sWorkbench).toMatch(/setTimeout\([\s\S]*,\s*100\s*\)/)
  })

  it('hardens Cesium interactions: disable LEFT_DOUBLE_CLICK tracking + vector swipe hook', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')

    // Avoid the "double-click boundary -> camera disaster" in demos.
    expect(sEngine).toMatch(/LEFT_DOUBLE_CLICK/)
    expect(sEngine).toMatch(/removeInputAction/)

    // Vector overlays (GeoJSON/entities) must at least have a swipe-cut hook.
    // Either true clipping planes (when supported) or a screen-space fallback.
    expect(sEngine).toMatch(/ClippingPlaneCollection|wgs84ToWindowCoordinates|SceneTransforms/)

    // Patch 0303: when swipe is enabled, overlays should be forced to the RIGHT.
    expect(sEngine).toMatch(/splitDirection\s*=\s*SD\.RIGHT/)
  })
})
