import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Zero2x landing wiring (TDD)', () => {
  it('mounts Zero2xApp on / and AlphaEarthApp on /demo', () => {
    const s = read('../src/main.js')
    expect(s).toContain("path === '/demo'")
    expect(s).toContain('Zero2xApp')
    expect(s).toContain('AlphaEarthApp')
  })

  it('Zero2xApp exposes Omni-Bar and CTA copy', () => {
    const s = read('../src/Zero2xApp.vue')
    expect(s).toContain('Press')
    expect(s).toContain('⌘K')
    expect(s).toContain('omnibar-kbd-hint')
    expect(s).toContain('Launch My Workspace')
    expect(s).toMatch(/workbench/i)
    expect(s).toContain('第二幕：宏观孪生')
    expect(s).toContain('第四幕：数据星海')
    expect(s).toContain('buildAct2ChoreoHref')
    expect(s).toContain('进入第二幕')
    expect(s).toContain('poyang')
    expect(s).toContain('DataGalaxy')
  })
})
