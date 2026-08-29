import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import {
  MISSION_CATEGORIES,
  getMissionCategory,
  filterMissionsByCategory,
  computeCategoryCounts,
} from '../src/utils/missionDeck.js'

function readAppVue() {
  const p = path.resolve(__dirname, '../src/App.vue')
  return fs.readFileSync(p, 'utf-8')
}

describe('missionDeck utilities', () => {
  const mockMissions = [
    { id: 'ch1_yuhang', name: '基因', title: '余杭城市基因', api_mode: 'ch1_yuhang_faceid' },
    { id: 'ch2_maowusu', name: '护盾', title: '毛乌素生态护盾', api_mode: 'ch2_maowusu_shield' },
    { id: 'ch3_zhoukou', name: '脉搏', title: '周口农田内涝', api_mode: 'ch3_zhoukou_pulse' },
    { id: 'ch4_amazon', name: '共识', title: '亚马逊毁林前线', api_mode: 'ch4_amazon_zeroshot' },
    { id: 'ch5_yancheng', name: '红线', title: '盐城海岸线红线审计', api_mode: 'ch5_coastline_audit' },
    { id: 'ch6_poyang', name: '脉动', title: '鄱阳湖水网脉动', api_mode: 'ch6_water_pulse' },
    { id: 'ch7_beijing', name: '定损', title: '极端暴雨灾害定损', api_mode: 'ch7_disaster_warning' },
    { id: 'ch7_guangdong', name: '预警', title: '汛期山洪与滑坡预警', api_mode: 'ch7_disaster_warning' },
    { id: '填海区沉降', name: '南沙沉降', title: '南沙填海造陆区固结监测', api_mode: 'ch8_insar_subsidence' },
    { id: '核心区沉降', name: '天河形变', title: '天河地下空间形变监测', api_mode: 'ch8_insar_subsidence' },
  ]

  it('defines the 4 primary categories', () => {
    expect(MISSION_CATEGORIES).toHaveLength(4)
    const keys = MISSION_CATEGORIES.map((c) => c.key)
    expect(keys).toEqual(['all', 'urban', 'ecology', 'hazard'])
  })

  it('correctly classifies missions into urban, ecology, and hazard', () => {
    expect(getMissionCategory(mockMissions[0])).toBe('urban') // ch1 yuhang
    expect(getMissionCategory(mockMissions[1])).toBe('ecology') // ch2 maowusu
    expect(getMissionCategory(mockMissions[2])).toBe('hazard') // ch3 zhoukou 内涝
    expect(getMissionCategory(mockMissions[3])).toBe('ecology') // ch4 amazon
    expect(getMissionCategory(mockMissions[4])).toBe('ecology') // ch5 yancheng
    expect(getMissionCategory(mockMissions[5])).toBe('ecology') // ch6 poyang
    expect(getMissionCategory(mockMissions[6])).toBe('hazard') // ch7 beijing 暴雨
    expect(getMissionCategory(mockMissions[7])).toBe('hazard') // ch7 guangdong 山洪
    expect(getMissionCategory(mockMissions[8])).toBe('urban') // ch8 nansha insar
    expect(getMissionCategory(mockMissions[9])).toBe('urban') // ch8 tianhe insar
  })

  it('computes category counts accurately', () => {
    const counts = computeCategoryCounts(mockMissions)
    expect(counts.all).toBe(10)
    expect(counts.urban).toBe(3)
    expect(counts.ecology).toBe(4)
    expect(counts.hazard).toBe(3)
  })

  it('filters missions by category key', () => {
    const all = filterMissionsByCategory(mockMissions, 'all')
    expect(all).toHaveLength(10)

    const urban = filterMissionsByCategory(mockMissions, 'urban')
    expect(urban).toHaveLength(3)
    expect(urban.every((m) => getMissionCategory(m) === 'urban')).toBe(true)

    const ecology = filterMissionsByCategory(mockMissions, 'ecology')
    expect(ecology).toHaveLength(4)
    expect(ecology.every((m) => getMissionCategory(m) === 'ecology')).toBe(true)

    const hazard = filterMissionsByCategory(mockMissions, 'hazard')
    expect(hazard).toHaveLength(3)
    expect(hazard.every((m) => getMissionCategory(m) === 'hazard')).toBe(true)
  })

  it('handles empty or invalid inputs gracefully', () => {
    expect(filterMissionsByCategory([], 'all')).toEqual([])
    expect(filterMissionsByCategory(null, 'urban')).toEqual([])
    expect(computeCategoryCounts(null)).toEqual({ all: 0, urban: 0, ecology: 0, hazard: 0 })
    expect(getMissionCategory(null)).toBe('urban')
  })
})

describe('App.vue Mission Deck Template & Aesthetics Guards', () => {
  it('contains the category tabs and navigation controls in the deck header', () => {
    const s = readAppVue()
    expect(s).toContain('class="deck-header"')
    expect(s).toContain('class="category-tabs"')
    expect(s).toContain('class="deck-nav-controls"')
    expect(s).toContain('class="nav-arrow-btn"')
  })

  it('contains the rail container with left/right shading masks', () => {
    const s = readAppVue()
    expect(s).toContain('class="rail-container"')
    expect(s).toContain('mask-left')
    expect(s).toContain('mask-right')
  })

  it('binds wheel event for natural horizontal scrolling', () => {
    const s = readAppVue()
    expect(s).toContain('@wheel="onRowWheel"')
    expect(s).toContain('onRowWheel')
  })

  it('defines 2-row horizontal grid styles', () => {
    const s = readAppVue()
    expect(s).toContain('grid-template-rows: repeat(2, minmax(')
    expect(s).toContain('grid-auto-flow: column')
    expect(s).toContain('scroll-snap-type: x proximity')
  })
})
