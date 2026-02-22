import { describe, it, expect } from 'vitest'
import {
  buildCommanderBrief,
  buildLegendHint,
  extractActionInsightsFromReport,
  extractTagline,
  getChapterCode,
  normalizeCommanderActionLine,
} from '../src/utils/missionBrief.js'

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
    expect(typeof brief.brief).toBe('string')
    expect(brief.brief.length).toBeGreaterThan(8)
    expect(typeof brief.mechanism).toBe('string')
    expect(brief.mechanism.length).toBeGreaterThan(6)
    expect(Array.isArray(brief.legends)).toBe(true)
    expect(brief.legends.length).toBeGreaterThan(0)
    expect(Array.isArray(brief.insights)).toBe(true)
    expect(brief.insights.length).toBeGreaterThan(0)
    expect(brief.insights.length).toBeLessThanOrEqual(3)

    expect(typeof brief.technical).toBe('string')
    expect(brief.technical).toContain('业务简报')
    expect(brief.technical).toContain('算法机理')
    expect(brief.technical).toContain('视觉图例')
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
      expect(brief.brief).toBeTruthy()
      expect(brief.mechanism).toBeTruthy()
      expect(brief.legends.length).toBeGreaterThan(0)
      for (const l of brief.legends) {
        expect(l.color).toMatch(colorRe)
        expect(l.label).toBeTruthy()
      }
      expect(brief.insights.length).toBeGreaterThan(0)
      expect(brief.insights.length).toBeLessThanOrEqual(3)

      expect(brief.technical).toBeTruthy()
      expect(brief.technical.length).toBeGreaterThan(120)
    }
  })

  it('chapter 1 and 6 legends match the playbook colors', () => {
    const ch1 = buildCommanderBrief('ch1_yuhang_faceid', { title: 'T', location: 'yuhang' }, null)
    expect(ch1.mechanism).toContain('欧氏距离')
    expect(ch1.legends.map((l) => l.color)).toContain('#FF4500')
    expect(ch1.legends.map((l) => l.color)).toContain('#111111')

    const ch6 = buildCommanderBrief('ch6_water_pulse', { title: 'T', location: 'poyang' }, null)
    expect(ch6.mechanism).toContain('差分')
    expect(ch6.legends.map((l) => l.color)).toContain('#1E4AFF')
    expect(ch6.legends.map((l) => l.color)).toContain('#FF5A36')
  })

  it('extractActionInsightsFromReport prefers suggestion line/section', () => {
    const report = [
      '《区域空间监测简报》',
      '任务：T',
      '统计：总面积 1.00 km²；异常占比 2.00%',
      '建议：对异常占比高的网格优先开展核查，结合 Sentinel-2 影像与历史变化趋势形成处置清单。',
    ].join('\n')

    const items = extractActionInsightsFromReport(report, 2)
    expect(Array.isArray(items)).toBe(true)
    expect(items.length).toBeGreaterThan(0)
    expect(items.length).toBeLessThanOrEqual(2)
    expect(items.join(' ')).toContain('优先')
  })

  it('extractActionInsightsFromReport prefers bullet list when present', () => {
    const report = [
      '简报',
      '建议：',
      '- 先核查红色连片区域',
      '- 对照 Sentinel-2 做复核',
      '- 形成台账闭环',
    ].join('\n')
    const items = extractActionInsightsFromReport(report, 2)
    expect(items).toEqual(['先核查红色连片区域', '对照 Sentinel-2 做复核'])
  })

  it('normalizeCommanderActionLine trims prefixes and punctuation', () => {
    expect(normalizeCommanderActionLine('建议：对异常占比高的网格优先开展核查。')).toContain('优先')
    expect(normalizeCommanderActionLine('请 结合 Sentinel-2 影像做复核；')).toBe('结合 Sentinel-2 影像做复核')
  })

  it('buildLegendHint formats a short reading rule', () => {
    const hint = buildLegendHint(
      [
        { color: '#1E4AFF', label: '蓝：水体扩张/恢复' },
        { color: '#FF5A36', label: '橙红：水体退缩/淤积' },
      ],
      2,
    )
    expect(hint).toContain('判读：')
    expect(hint).toContain('蓝=水体扩张/恢复')
  })
})
