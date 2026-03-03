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
    expect(s).toMatch(/workbench/i)

    // Branding upgrade: emphasize tool/product identity (update_patch_0303).
    expect(s).toContain('AI-Native 渐进式科研工作台')
    expect(s).toContain('第二幕：宏观孪生')
    expect(s).toContain('第四幕：数据星海')
    expect(s).toContain('poyang')

    // Act 4 is videoized (no heavy WebGL galaxy on landing).
    expect(s).toContain('act4_galaxy')

    // Act 5 is an integrated workbench preview (glass IDE over viewport).
    expect(s).toContain('workbench-integrated')
    expect(s).toContain('workbench-bg-viewport')
    expect(s).toContain('ide-frame')
    expect(s).toContain('AGENT_FLOW')

    // Act 5 scaling stability: center-aim must be physically centered.
    expect(s).toContain('hud-center-aim-container')

    // Act 5 launch passes the selected scenario context into the heavy workbench route.
    expect(s).toContain('/workbench?context=')
    expect(s).toContain("ref('poyang')")
  })
})
