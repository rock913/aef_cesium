import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('v7.2 WebGPU sandbox contracts', () => {
  it('EngineRouter provides a DOM overlay canvas and postRender sync hooks', () => {
    const sEngine = read('../src/views/workbench/EngineRouter.vue')

    // DOM overlay approach: GPU canvas stacked above Cesium.
    expect(sEngine).toMatch(/<canvas[^>]*ref="gpuCanvas"/)
    expect(sEngine).toMatch(/showWebGPU/)
    expect(sEngine).toMatch(/pointer-events-none|pointerEvents\s*:\s*'none'/)

    // Event-driven sync: must reference scene.postRender (avoid requestAnimationFrame loops).
    expect(sEngine).toMatch(/scene\.(postRender|postUpdate)/)

    // WebGPU entrypoint: navigator.gpu.requestAdapter() is the canonical bootstrap.
    expect(sEngine).toMatch(/navigator\.gpu\.(requestAdapter|requestDevice)/)

    // Hardware limits sniffing (adaptive degradation) should be present.
    expect(sEngine).toMatch(/device\.limits\./)

    // Minimal demo-safe compute+render example should exist (not just a clear pass).
    expect(sEngine).toMatch(/createComputePipeline/)
    expect(sEngine).toMatch(/createRenderPipeline/)

    // Demo 11 visual-impact patch: night mode should tune base imagery layers.
    expect(sEngine).toMatch(/imageryLayers/)
    expect(sEngine).toMatch(/brightness/)
    expect(sEngine).toMatch(/contrast/)
  })

  it('Workbench handles v7.2 tool calls for subsurface + dynamic WGSL execution', () => {
    const sWorkbench = read('../src/WorkbenchApp.vue')

    // New v7.2 tools should be consumed in applyCopilotEvents.
    expect(sWorkbench).toMatch(/tool\s*===\s*'enable_subsurface_mode'/)
    expect(sWorkbench).toMatch(/tool\s*===\s*'disable_subsurface_mode'/)
    expect(sWorkbench).toMatch(/tool\s*===\s*'add_subsurface_model'/)
    expect(sWorkbench).toMatch(/tool\s*===\s*'execute_dynamic_wgsl'/)
    expect(sWorkbench).toMatch(/tool\s*===\s*'destroy_webgpu_sandbox'/)

    // execute_dynamic_wgsl must write into the editor/code artifact.
    expect(sWorkbench).toMatch(/code\.value\s*=|write_to_editor/i)
  })
})
