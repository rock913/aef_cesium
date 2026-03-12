import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('0303 WebGPU raw-mode clip-space contracts', () => {
  it('EngineRouter applies a projection clip-fix for mode=raw (best-effort)', () => {
    const s = read('../src/views/workbench/EngineRouter.vue')

    // Guard: raw mode exists as a candidate.
    expect(s).toMatch(/mode:\s*'raw'/)

    // Contract: raw modules may need WebGL->WebGPU Z mapping; engine pre-multiplies proj.
    expect(s).toMatch(/selectedMode\s*===\s*'raw'/)
    expect(s).toMatch(/rawMayNeedProjClipFix/)
    expect(s).toMatch(/Matrix4\.multiply\(\s*_clipFix\s*,\s*proj\s*,\s*_projScratch\s*\)/)
  })
})
