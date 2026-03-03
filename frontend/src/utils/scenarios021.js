/**
 * 021 demo scenarios for the Zero2x landing + workbench handoff.
 *
 * This module is intentionally lightweight so it can be imported by Landing
 * without pulling heavy runtime deps (Cesium/Monaco).
 */

export const scenarios021 = [
  {
    id: 'poyang',
    label: '国家水网脉动：鄱阳湖生态监测',
    targetName: '江西 · 鄱阳湖流域',
    action: '正在提取 64 维空间特征...',
    targetId: 'lake_poyang_coord',
    layer: 'Water_Fluctuation',
    backend: {
      location: 'poyang',
      mode: 'ch6_water_pulse',
    },
    camera: { lat: 29.20, lon: 116.20, height: 95000, duration_s: 4.0, pitch_deg: -42.0 },
  },
  {
    id: 'yuhang',
    label: '城市基因突变：杭州余杭城建审计',
    targetName: '杭州 · 余杭未来科技城',
    action: '执行欧氏距离算子...',
    targetId: 'city_yuhang_coord',
    layer: 'Urban_Mutation',
    backend: {
      location: 'yuhang',
      mode: 'ch1_yuhang_faceid',
    },
    camera: { lat: 30.26879, lon: 119.92284, height: 16000, duration_s: 3.8, pitch_deg: -45.0 },
  },
  {
    id: 'amazon',
    label: '行星级零样本聚类：亚马逊雨林切分',
    targetName: '巴西 · 亚马逊雨林',
    action: '启动无监督聚类算法...',
    targetId: 'forest_amazon_coord',
    layer: 'Zero_Shot_Clustering',
    backend: {
      location: 'amazon',
      mode: 'ch4_amazon_zeroshot',
    },
    camera: { lat: -10.04485, lon: -55.42936, height: 90000, duration_s: 4.0, pitch_deg: -42.0 },
  },
]

export function getScenario021ById(id) {
  const key = String(id || '').trim().toLowerCase()
  return scenarios021.find((s) => s.id === key) || null
}

export function getDefaultScenario021() {
  return getScenario021ById('poyang') || scenarios021[0] || null
}

export function parseWorkbenchContextFromSearch(search) {
  try {
    const qs = typeof search === 'string' ? search : ''
    const sp = new URLSearchParams(qs.startsWith('?') ? qs : `?${qs}`)
    const ctx = String(sp.get('context') || '').trim()
    return ctx
  } catch (_) {
    return ''
  }
}
