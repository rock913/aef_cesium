import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Act-2 narrative scene isolation (TDD gate)', () => {
  it('Act2App stays narrative-only (no Missions/API imports)', () => {
    const s = read('../src/Act2App.vue')

    // Must use CesiumViewer primitive
    expect(s).toContain("from './components/CesiumViewer.vue'")

    // Must NOT pull demo workflow/data layer
    expect(s).not.toContain("from './services/api")
    expect(s).not.toContain('apiService')

    // Must NOT embed Demo state machine / missions workflow
    expect(s).not.toContain('lockMission')
    expect(s).not.toContain('runAgenticWorkflow')
    expect(s).not.toContain('prefetchMissions')
    expect(s).not.toContain('mission-card')
    expect(s).not.toContain('HudPanel')
    expect(s).not.toContain('missionBrief')
  })

  it('Act2App provides explicit escape hatches', () => {
    const s = read('../src/Act2App.vue')
    expect(s).toContain('Back to Landing')
    expect(s).toContain('Open Demo')
    expect(s).toContain('Replay FlyTo')
  })
})
