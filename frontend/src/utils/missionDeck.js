export const MISSION_CATEGORIES = [
  { key: 'all', label: '全部', icon: '🌐' },
  { key: 'urban', label: '城市基建', icon: '🏙️' },
  { key: 'ecology', label: '生态环境', icon: '🌿' },
  { key: 'hazard', label: '应急防汛', icon: '⚠️' },
]

/**
 * Classifies a mission into one of the core categories: 'urban', 'ecology', or 'hazard'.
 * @param {Object} m Mission object
 * @returns {'urban'|'ecology'|'hazard'}
 */
export function getMissionCategory(m) {
  if (!m) return 'urban'
  const id = String(m.id || '').toLowerCase()
  const mode = String(m.api_mode || '').toLowerCase()
  const text = (String(m.title || '') + ' ' + String(m.name || '') + ' ' + String(m.formula || '')).toLowerCase()

  if (
    mode.includes('insar') ||
    mode.includes('yuhang') ||
    id.includes('沉降') ||
    text.includes('城市') ||
    text.includes('基建') ||
    text.includes('地下空间') ||
    text.includes('填海')
  ) {
    return 'urban'
  }
  if (
    mode.includes('maowusu') ||
    mode.includes('amazon') ||
    mode.includes('coastline') ||
    mode.includes('water_pulse') ||
    text.includes('生态') ||
    text.includes('毁林') ||
    text.includes('红线') ||
    text.includes('水网') ||
    text.includes('鄱阳湖')
  ) {
    return 'ecology'
  }
  if (
    mode.includes('zhoukou') ||
    mode.includes('disaster') ||
    text.includes('灾害') ||
    text.includes('内涝') ||
    text.includes('暴雨') ||
    text.includes('滑坡') ||
    text.includes('山洪')
  ) {
    return 'hazard'
  }
  return 'urban'
}

/**
 * Filters a list of missions by category key.
 * @param {Array} missions
 * @param {string} categoryKey 'all' | 'urban' | 'ecology' | 'hazard'
 * @returns {Array}
 */
export function filterMissionsByCategory(missions, categoryKey) {
  if (!Array.isArray(missions) || !missions.length) return []
  if (!categoryKey || categoryKey === 'all') return missions
  return missions.filter((m) => getMissionCategory(m) === categoryKey)
}

/**
 * Computes counts of missions grouped by category.
 * @param {Array} missions
 * @returns {Record<string, number>}
 */
export function computeCategoryCounts(missions) {
  const counts = { all: Array.isArray(missions) ? missions.length : 0, urban: 0, ecology: 0, hazard: 0 }
  if (!Array.isArray(missions)) return counts
  for (const m of missions) {
    const cat = getMissionCategory(m)
    if (counts[cat] !== undefined) {
      counts[cat]++
    }
  }
  return counts
}
