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
      mission_id: 'ch6_poyang',
    },
    hasTime: true,
    timeRange: { minYear: 2020, maxYear: 2026 },
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
      mission_id: 'ch1_yuhang',
    },
    hasTime: true,
    timeRange: { minYear: 2017, maxYear: 2024 },
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
      mission_id: 'ch4_amazon',
    },
    camera: { lat: -10.04485, lon: -55.42936, height: 90000, duration_s: 4.0, pitch_deg: -42.0 },
  },
  {
    id: 'maowusu',
    label: '生态护盾穿透：毛乌素沙地治理成效评估',
    targetName: '内蒙古/陕西交界 · 毛乌素沙地',
    action: '执行余弦相似度生态穿透...',
    targetId: 'desert_maowusu_coord',
    layer: 'Eco_Shield',
    backend: {
      location: 'maowusu',
      mode: 'ch2_maowusu_shield',
      mission_id: 'ch2_maowusu',
    },
    hasTime: true,
    timeRange: { minYear: 2019, maxYear: 2024 },
    camera: { lat: 38.60, lon: 109.60, height: 70000, duration_s: 3.9, pitch_deg: -42.0 },
  },
  {
    id: 'yancheng',
    label: '海岸线红线审计：盐城湿地边界智能划界',
    targetName: '江苏 · 盐城湿地海岸线',
    action: '执行红线边界提取...',
    targetId: 'coast_yancheng_coord',
    layer: 'Coastline_Audit',
    backend: {
      location: 'yancheng',
      mode: 'ch5_coastline_audit',
      mission_id: 'ch5_yancheng',
    },
    camera: { lat: 33.38, lon: 120.50, height: 95000, duration_s: 4.0, pitch_deg: -42.0 },
  },
  {
    id: 'zhoukou',
    label: '粮仓脉搏体检：周口农田内涝胁迫预警',
    targetName: '河南 · 周口农田',
    action: '反演内涝胁迫风险...',
    targetId: 'farm_zhoukou_coord',
    layer: 'Water_Stress',
    backend: {
      location: 'zhoukou',
      mode: 'ch3_zhoukou_pulse',
      mission_id: 'ch3_zhoukou',
    },
    camera: { lat: 33.63, lon: 114.65, height: 70000, duration_s: 4.0, pitch_deg: -42.0 },
  },

  // v7.1 forward demos: provide camera targets, keep backend bindings optional.
  { id: 'talatan', label: '光伏蓝海：塔拉滩产业园', targetName: '青海 · 塔拉滩', action: '加载光伏与生物量…', targetId: 'pv_talatan_coord', layer: 'PV_Blue', backend: null, camera: { lat: 36.10, lon: 101.70, height: 180000, duration_s: 4.2, pitch_deg: -40.0 } },
  { id: 'everest_lake', label: '冰川湖溃决：珠峰北坡', targetName: '喜马拉雅 · 珠峰北坡冰川湖', action: '体积测算与路径模拟…', targetId: 'everest_lake_coord', layer: 'GLOF', backend: null, camera: { lat: 28.04, lon: 86.93, height: 220000, duration_s: 4.4, pitch_deg: -38.0 } },
  { id: 'mauna_loa', label: '火山预判：冒纳罗亚', targetName: '夏威夷 · 冒纳罗亚火山', action: '加载 InSAR + 热异常…', targetId: 'mauna_loa_coord', layer: 'Volcano', backend: null, camera: { lat: 19.48, lon: -155.61, height: 240000, duration_s: 4.4, pitch_deg: -38.0 } },
  { id: 'congo', label: '碳汇估算：刚果盆地', targetName: '非洲 · 刚果盆地', action: '估算三维生物量…', targetId: 'congo_coord', layer: 'Carbon', backend: null, camera: { lat: -1.20, lon: 23.70, height: 320000, duration_s: 4.6, pitch_deg: -36.0 } },
  { id: 'nyc', label: '热岛 × 脆弱性：纽约都会区', targetName: '美国 · 纽约都会区', action: '计算相关性…', targetId: 'nyc_coord', layer: 'Heat_Vuln', backend: null, camera: { lat: 40.71, lon: -74.00, height: 180000, duration_s: 4.0, pitch_deg: -40.0 } },
  { id: 'malacca', label: '暗夜油污追踪：马六甲海峡', targetName: '马六甲海峡', action: '检测油污 + AIS 溯源…', targetId: 'malacca_coord', layer: 'OilSpill', backend: null, camera: { lat: 2.50, lon: 101.00, height: 420000, duration_s: 4.8, pitch_deg: -34.0 } },
  { id: 'pilbara', label: '高光谱解译：皮尔巴拉', targetName: '澳大利亚 · 皮尔巴拉矿区', action: '执行光谱解混…', targetId: 'pilbara_coord', layer: 'Minerals', backend: null, camera: { lat: -22.30, lon: 118.70, height: 520000, duration_s: 5.0, pitch_deg: -32.0 } },

  // Demo 13 (v7.1): global view for code-generation / wind field rendering.
  { id: 'global', label: '全球风场流体：代码热生成', targetName: '全球视角', action: '生成 GLSL + 绑定风场纹理…', targetId: 'global_coord', layer: 'Wind', backend: null, camera: { lat: 0.0, lon: 0.0, height: 12000000, duration_s: 4.2, pitch_deg: -55.0 } },
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
