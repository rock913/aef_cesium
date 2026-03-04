import { describe, it, expect } from 'vitest'
import { getScenario021ById, scenarios021 } from '../src/utils/scenarios021.js'

describe('021 scenario registry (workbench handoff)', () => {
  it('includes core demo contexts', () => {
    const ids = new Set((scenarios021 || []).map((s) => s.id))
    expect(ids.has('poyang')).toBe(true)
    expect(ids.has('yuhang')).toBe(true)
    expect(ids.has('amazon')).toBe(true)
    expect(ids.has('maowusu')).toBe(true)
    expect(ids.has('yancheng')).toBe(true)
    expect(ids.has('zhoukou')).toBe(true)
    expect(ids.has('global')).toBe(true)
  })

  it('resolves maowusu without fallback', () => {
    const s = getScenario021ById('maowusu')
    expect(s).toBeTruthy()
    expect(s.id).toBe('maowusu')
    expect(s.camera).toBeTruthy()
    expect(Number.isFinite(Number(s.camera.lat))).toBe(true)
    expect(Number.isFinite(Number(s.camera.lon))).toBe(true)
  })
})
