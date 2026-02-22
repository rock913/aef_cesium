import { describe, it, expect } from 'vitest'
import { buildCommanderBrief, extractTagline, getChapterCode } from '../src/utils/missionBrief.js'

describe('missionBrief', () => {
  it('extractTagline returns first sentence', () => {
    const t = extractTagline('第一句很关键。第二句不应该出现。')
    expect(t).toBe('第一句很关键')
  })

  it('getChapterCode parses chN', () => {
    expect(getChapterCode('ch6_poyang')).toBe('CH6')
  })

  it('buildCommanderBrief returns mechanism/legends/insights', () => {
    const brief = buildCommanderBrief('ch1_yuhang_faceid', { title: 'T' }, { total_area_km2: 1, anomaly_pct: 2 })
    expect(typeof brief.mechanism).toBe('string')
    expect(brief.mechanism.length).toBeGreaterThan(6)
    expect(Array.isArray(brief.legends)).toBe(true)
    expect(brief.legends.length).toBeGreaterThan(0)
    expect(Array.isArray(brief.insights)).toBe(true)
    expect(brief.insights.length).toBeGreaterThan(0)
    expect(brief.insights.length).toBeLessThanOrEqual(3)
  })

  it('all six modes provide at least one legend and 1-3 insights', () => {
    const modes = [
      'ch1_yuhang_faceid',
      'ch2_maowusu_shield',
      'ch3_zhoukou_pulse',
      'ch4_amazon_zeroshot',
      'ch5_coastline_audit',
      'ch6_water_pulse',
    ]

    const colorRe = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

    for (const modeId of modes) {
      const brief = buildCommanderBrief(modeId, { title: 'T', location: 'x' }, { total_area_km2: 1, anomaly_area_km2: 0.2, anomaly_pct: 3 })
      expect(brief.mechanism).toBeTruthy()
      expect(brief.legends.length).toBeGreaterThan(0)
      for (const l of brief.legends) {
        expect(l.color).toMatch(colorRe)
        expect(l.label).toBeTruthy()
      }
      expect(brief.insights.length).toBeGreaterThan(0)
      expect(brief.insights.length).toBeLessThanOrEqual(3)
    }
  })
})
