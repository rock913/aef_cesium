import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench demo copy (no placeholders)', () => {
  it('removes placeholder wording from the visible demo flow', () => {
    const s = read('../src/WorkbenchApp.vue')

    expect(s).not.toContain('(placeholder)')
    expect(s).not.toContain('Placeholder')
    expect(s).toContain('Agent (demo):')
    expect(s).toContain("sessionStorage?.getItem?.('z2x:lastContext')")

    // zero2x_v6: Spatial IDE layout (Analytical by default, Immersive via F11).
    expect(s).toMatch(/沉浸模式|Immersive/i)
    expect(s).toContain('F11')
    expect(s).toMatch(/<aside[\s>]/)
    expect(s).toMatch(/EngineRouter|engine-router/i)
    expect(s).toMatch(/Cmd\+K|Ctrl\+K|⌘K|OmniCommand/i)

    // Explicit mode toggle (top-center, leader-visible)
    expect(s).toMatch(/Mode Toggle|显性|拨片|切换/i)
    expect(s).toMatch(/Theater/i)
    expect(s).toMatch(/Lab/i)

    // Stateful demo presets: scenario + UI state binding
    expect(s).toMatch(/demoPresets|Stateful|预置演示/i)

    // Tab system: twin + table + charts
    expect(s).toMatch(/Tab System|TabBar|Twin View/i)
    expect(s).toMatch(/Data Table/i)
    expect(s).toMatch(/2D Charts/i)

    // Theater HUD + layer tree widgets
    expect(s).toMatch(/TheaterHUD|核心研判结论/i)
    expect(s).toMatch(/LayerTree|LAYER TREE/i)
  })
})
