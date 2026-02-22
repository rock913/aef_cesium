// Leadership-friendly mission brief model for the “Commander Panel” UI.
// Keeps text short (what / where / what to do) and supplies a legend that matches backend palettes.

function _fmtNum(x, digits = 2) {
  if (x === null || x === undefined) return '—'
  const n = Number(x)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(digits)
}

export function extractTagline(narrative) {
  if (!narrative || typeof narrative !== 'string') return ''
  const s = narrative
    .replace(/\s+/g, ' ')
    .replace(/[。！？!？]+/g, '。')
    .trim()
  if (!s) return ''
  const first = s.split('。')[0]?.trim()
  if (!first) return s.slice(0, 36)
  return first.length > 42 ? first.slice(0, 42) + '…' : first
}

export function getChapterCode(missionId) {
  // missionId like: ch1_yuhang
  if (!missionId || typeof missionId !== 'string') return ''
  const m = missionId.match(/^(ch\d+)/)
  return m ? m[1].toUpperCase() : ''
}

export function buildCommanderBrief(modeId, mission, stats) {
  const totalKm2 = stats?.total_area_km2
  const anomalyKm2 = stats?.anomaly_area_km2
  const anomalyPct = stats?.anomaly_pct

  const commonInsights = []

  // Stats sentence: keep it short; ch4/ch5 are categorical so “异常” may be N/A
  if (typeof totalKm2 === 'number' && !Number.isNaN(totalKm2)) {
    if (typeof anomalyPct === 'number' && !Number.isNaN(anomalyPct)) {
      commonInsights.push(`总面积 ${_fmtNum(totalKm2)} km²，异常占比 ${_fmtNum(anomalyPct)}%。`)
    } else if (typeof anomalyKm2 === 'number' && !Number.isNaN(anomalyKm2)) {
      commonInsights.push(`总面积 ${_fmtNum(totalKm2)} km²，异常面积 ${_fmtNum(anomalyKm2)} km²。`)
    } else {
      commonInsights.push(`分析总面积 ${_fmtNum(totalKm2)} km²。`)
    }
  }

  const title = mission?.title || ''
  const location = mission?.location || ''

  // Defaults
  let mechanism = '基于 AEF 年度表征做空间对比，输出可视化热区与统计指标。'
  let legends = [{ color: '#00F5FF', label: '高亮：值得关注的结构变化' }]
  let insights = []

  if (modeId === 'ch1_yuhang_faceid') {
    mechanism = '对比 2017 vs 2024 的语义表征距离，只保留“结构性突变”区域。'
    legends = [
      { color: '#FF0000', label: '红/橙：突变区（新增建设/基建）' },
      { color: '#111111', label: '深色：稳定区' },
    ]
    insights = [
      ...commonInsights,
      '优先核查红色连片区域：对照城建台账形成审计结论。',
    ]
  } else if (modeId === 'ch2_maowusu_shield') {
    mechanism = '用余弦相似度只看“语义方向”，降低季节枯黄/光照扰动。'
    legends = [
      { color: '#00AA66', label: '绿：语义方向一致（更稳定）' },
      { color: '#FF3300', label: '红：语义方向偏离（需要复核）' },
    ]
    insights = [
      ...commonInsights,
      '若冬季仍显示稳定，意味着“生态骨架”已形成，可用于对外共识印证。',
    ]
  } else if (modeId === 'ch3_zhoukou_pulse') {
    mechanism = '抽取对农田胁迫敏感的特定维度（示意 A02），生成可解释的强度场。'
    legends = [
      { color: '#00A3FF', label: '蓝：胁迫/内涝风险更高' },
      { color: '#E0FFFF', label: '浅色：背景正常' },
    ]
    insights = [
      ...commonInsights,
      '将蓝色热点作为“优先排水/核查网格”，联动 Sentinel-2 或现场核验。',
    ]
  } else if (modeId === 'ch4_amazon_zeroshot') {
    mechanism = '零样本聚类切分结构单元（森林/开荒带/水系等），用于快速识别格局。'
    legends = [
      { color: '#999999', label: '不同颜色代表不同结构分区（类别图，不等同“异常”）' },
    ]
    insights = [
      '关注“鱼骨状”边界与道路廊道：它们往往指向新增人类活动带。',
    ]
  } else if (modeId === 'ch5_coastline_audit') {
    mechanism = '用 A00/A02 做半监督聚类，快速划分海域/陆域/潮间带等审计单元。'
    legends = [
      { color: '#0B1B36', label: '深蓝：稳定陆域/硬化带' },
      { color: '#E23D28', label: '红：海域/水体单元' },
      { color: '#F6C431', label: '金：潮间带/滩涂过渡带' },
    ]
    insights = [
      '将“金色过渡带”与红线/围垦边界叠加：优先锁定潜在越界占用点。',
    ]
  } else if (modeId === 'ch6_water_pulse') {
    mechanism = '对 2024-2022 的 A02 做差分并阈值掩膜，突出水网/湿地显著波动带。'
    legends = [
      { color: '#1E4AFF', label: '蓝：水体扩张/恢复' },
      { color: '#FF5A36', label: '橙红：水体退缩/淤积' },
    ]
    insights = [
      ...commonInsights,
      '把蓝/红对照到水位/降雨记录：形成“丰枯变化 + 风险点位”汇报口径。',
    ]
  } else {
    // Fallback: stay generic but still helpful
    insights = [
      ...commonInsights,
      `任务：${title || '—'}（${location || '—'}）`,
    ]
  }

  // Clamp insights to 1–3 bullets for the typewriter UI.
  const finalInsights = insights.filter(Boolean).slice(0, 3)

  return {
    mechanism,
    legends,
    insights: finalInsights,
  }
}
