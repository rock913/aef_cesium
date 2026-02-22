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

function _buildStatsLine(stats) {
  const totalKm2 = stats?.total_area_km2
  const anomalyKm2 = stats?.anomaly_area_km2
  const anomalyPct = stats?.anomaly_pct

  const parts = []
  if (typeof totalKm2 === 'number' && !Number.isNaN(totalKm2)) {
    parts.push(`分析总面积: ${_fmtNum(totalKm2)} km²`)
  }
  if (typeof anomalyKm2 === 'number' && !Number.isNaN(anomalyKm2)) {
    parts.push(`异常面积: ${_fmtNum(anomalyKm2)} km²`)
  }
  if (typeof anomalyPct === 'number' && !Number.isNaN(anomalyPct)) {
    parts.push(`异常占比: ${_fmtNum(anomalyPct)}%`)
  }

  return parts.length ? parts.join(' | ') : '区域统计: —'
}

function _buildTechnicalOutput({ mission, modeId, operator, brief, mechanism, legends, technicalInsights, stats }) {
  const title = mission?.title || mission?.name || '—'
  const loc = mission?.location || '—'
  const chapter = getChapterCode(mission?.id || '') || getChapterCode(modeId) || '—'

  const statsLine = _buildStatsLine(stats)
  const legendLines = Array.isArray(legends) && legends.length
    ? legends.map((l) => `- ${String(l?.label || '').trim()}`).filter(Boolean)
    : ['- —']

  const insightLines = Array.isArray(technicalInsights) && technicalInsights.length
    ? technicalInsights.map((s) => `- ${String(s).trim()}`).filter(Boolean)
    : ['- —']

  return [
    '《Alpha Earth Foundation 技术版输出》',
    `任务: ${title} (${chapter} / ${loc})`,
    `核心算子: ${operator || '—'}`,
    statsLine.startsWith('区域统计:') ? statsLine : `区域统计: ${statsLine}`,
    '',
    '业务简报 (Brief)',
    String(brief || '—').trim(),
    '',
    '算法机理',
    String(mechanism || '—').trim(),
    '',
    '视觉图例',
    ...legendLines,
    '',
    '核心洞察',
    ...insightLines,
    '',
  ].join('\n')
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
  let operator = ''
  let brief = '基于 AEF（64 维特征向量）对地表进行“Face ID”式对比与解构，输出可视化热区与统计指标。'
  let mechanism = '基于 AEF 年度表征做空间对比，输出可视化热区与统计指标。'
  let legends = [{ color: '#00F5FF', label: '高亮区域：值得关注的结构变化' }]
  let insights = []
  let technicalInsights = []

  if (modeId === 'ch1_yuhang_faceid') {
    operator = 'EuclideanDistance(V_2017, V_2024)'
    brief = '中国数字经济的心脏地带，7 年间从城郊荒地变为高新产业矩阵。AEF 以欧氏距离锁定人类建筑对自然地表的彻底重写，作为不可篡改的城建审计铁证。'
    mechanism = '欧氏距离：提取 2017 与 2024 年底座 64 维向量的欧氏距离，过滤微小变化，锁定彻底的物理重构。'
    legends = [
      { color: '#FF4500', label: '红黄高亮区域：特征剧烈变异区（新增建筑/基建）' },
      { color: '#111111', label: '深色暗影区域：地表特征稳定区' },
    ]
    insights = [
      ...commonInsights,
      '优先核查高亮连片区域：对照城建台账形成审计结论。',
    ]
    technicalInsights = [
      `[异动感知] 扫描比对显示，2017 至 2024 年间底层物理空间发生显著变化${typeof anomalyKm2 === 'number' ? `，异常面积约 ${_fmtNum(anomalyKm2)} km²` : ''}${typeof anomalyPct === 'number' ? `（${_fmtNum(anomalyPct)}%）` : ''}。`,
      '[归因分析] 变异轨迹与重大园区、大科学装置、基础设施建设进程高度吻合。',
      '[行动建议] 将高亮网格列入优先核查清单，联动城建台账形成客观审计结论。',
    ]
  } else if (modeId === 'ch2_maowusu_shield') {
    operator = 'CosineSimilarity(V_2019, V_2024)'
    brief = '联合国认可的治沙奇迹。传统遥感在秋冬季枯黄极易被质疑为“伪绿化”；AEF 以余弦相似度只看语义方向，强力证明退增的不是季节落叶，而是固定的防风林。'
    mechanism = '余弦相似度：只看“语义方向”不看“大小”，排除秋冬枯黄与光照干扰。'
    legends = [
      { color: '#FF4500', label: '橙红/亮红区域：生态本质跃迁（沙漠向绿洲转化）' },
      { color: '#006400', label: '深绿/深蓝色区：原有地貌结构保持稳定' },
    ]
    insights = [
      ...commonInsights,
      '若枯黄季节仍显示稳定，意味着“生态骨架”已成型，可用于共识印证与成效复核。',
    ]
    technicalInsights = [
      `[异动感知] 2019–2024 年核心区呈现大面积显著特征重构${typeof anomalyPct === 'number' ? `，异常变化占比约 ${_fmtNum(anomalyPct)}%` : ''}。`,
      '[归因分析] 余弦算法成功剥离季节假象，确证从流动沙丘向固定灌木林的不可逆跃迁。',
      '[共识印证] “治沙奇迹”在 64 维空间得到数学验证，可用于质疑场景下的成效复核。',
    ]
  } else if (modeId === 'ch3_zhoukou_pulse') {
    operator = 'InverseSpecificDimension(A02)'
    brief = '光学影像仍是“绿油油的麦田”，但 A02 融合了微波介电常数响应，可透视根系缺氧、倒伏等隐形危机，在减产前发出预警。'
    mechanism = '特定维度反演：抽取对农田胁迫极度敏感的 A02 维度，生成可解释的健康强度场。'
    legends = [
      { color: '#00F5FF', label: '亮青色/蓝色斑块：显著的农作物隐形衰退/内涝区' },
      { color: '#E0FFFF', label: '浅白/透明背景：正常农田生长背景' },
    ]
    insights = [
      ...commonInsights,
      '优先核查高异常网格对应田块的地下水位与土壤含水量。',
      '评估排水沟渠清淤/田间暗管布设，实施精准排涝。',
    ]
    technicalInsights = [
      '[快速响应] 优先核查 AEF-A02 高异常网格对应田块的地下水位与土壤剖面含水量。',
      '[治理干预] 评估排水沟渠清淤与田间暗管布设可行性，实施精准排涝以降低减产风险。',
    ]
  } else if (modeId === 'ch4_amazon_zeroshot') {
    operator = 'ZeroShotKMeans(k=6)'
    brief = '不给 AI 输入任何南美洲先验知识，直接一键聚类：系统自动切分原始林、砍伐鱼骨、水域等单元，证明 Alpha Earth Foundation 具备全球即插即用的通用智能能力。'
    mechanism = '零样本聚类：未输入样本标签，直接在 64 维空间执行无监督聚类，自动切分结构单元。'
    legends = [
      { color: '#006400', label: '暗绿色图斑：连片的原始热带雨林' },
      { color: '#FF1493', label: '粉红/紫红图斑：鱼骨状开荒带与人类活动区' },
      { color: '#F6C431', label: '橙黄图斑：次生演替带或裸露土壤' },
    ]
    insights = [
      '关注“鱼骨状”边界与道路廊道：它们往往指向新增人类活动带。',
      '可将紫红带与保护区边界叠加，生成巡查优先级清单。',
    ]
    technicalInsights = [
      '[异动感知] 算力集群可在秒级自动切分复杂的生态割裂网络与砍伐边界。',
      '[归因分析] 无需人为教导，AI 在向量空间内自主内化地表结构差异与演变规则。',
      '[战略价值] 具备全球泛化与即插即用能力，可作为空间治理公共科技底座。',
    ]
  } else if (modeId === 'ch5_coastline_audit') {
    operator = 'RF-Supervised(16-Dim) + Asset'
    brief = '面向“离任生态审计/自然岸线保有率”场景：以 AEF 16 维特征为输入，使用锚点多边形监督训练随机森林，并固化为 GEE Asset，生产推理毫秒级、语义稳定不漂移。'
    mechanism = '监督分类（随机森林）：用多边形锚点采样 16 维特征，训练分类器并资产化；运行时直接 load 资产并 classify，避免每次视口变化重新训练导致的标签漂移。'
    legends = [
      { color: '#1A365D', label: '深蓝：水域（含长江口浑浊水）' },
      { color: '#F6C431', label: '金黄：自然滩涂/泥沙沉积带' },
      { color: '#E23D28', label: '警告红：人工围垦/硬化堤坝/高强度开发斑块' },
    ]
    insights = [
      '将红色高强度斑块与红线边界叠加，生成核查点位清单。',
      '对“金黄滩涂”连片区做保有率统计，形成审计量化指标。',
    ]
    technicalInsights = [
      '[稳健推理] 分类器资产化后，语义绑定固定：蓝=水、黄=滩涂、红=围垦硬化，避免标签漂移与渲染闪烁。',
      '[高并发] 运行期不再采样/训练，拖拽视口也不会触发云端重训，显著降低超时与成本。',
      '[审计输出] 可直接用于“自然岸线保有率”核算、红线预警与离任生态审计举证底图。',
    ]
  } else if (modeId === 'ch6_water_pulse') {
    operator = 'ΔA02(2024 - 2022)'
    brief = '以 A02 跨年差分突出水体/湿地结构变异演化，捕捉水网连通性波动并量化淡水盈亏，为生态水文协同治理提供宏观账本。'
    mechanism = '跨年差分：提取对含水量/淹没状态敏感的 A02 维度，做 2024-2022 差分以量化水网与湿地消长。'
    legends = [
      { color: '#1E4AFF', label: '亮蓝色：水体扩张与洲滩湿地恢复区' },
      { color: '#FF5A36', label: '橙红色：水体持续退缩或泥沙淤积带' },
    ]
    insights = [
      ...commonInsights,
      '优先核查都昌—星子段主航道高值区的水下地形与连通性变化。',
      '联动水利调度日志与时序影像，评估调蓄工程对生态水网的干预效能。',
    ]
    technicalInsights = [
      '[勘测指令] 优先核查都昌—星子段主航道 ΔA02 高值区的水下地形与河床连通性变化。',
      '[协同联动] 比对同期闸坝调度日志与遥感时序，评估调蓄工程对生态水网的真实干预效能。',
    ]
  } else {
    // Fallback: stay generic but still helpful
    operator = 'AEF(64D) change scan'
    insights = [
      ...commonInsights,
      `任务：${title || '—'}（${location || '—'}）`,
    ]
    technicalInsights = insights.slice(0)
  }

  // Clamp insights to 1–3 bullets for the typewriter UI.
  const finalInsights = insights.filter(Boolean).slice(0, 3)

  const technical = _buildTechnicalOutput({
    mission,
    modeId,
    operator,
    brief,
    mechanism,
    legends,
    technicalInsights,
    stats,
  })

  return {
    brief,
    mechanism,
    legends,
    insights: finalInsights,
    technical,
  }
}

function _stripBulletPrefix(line) {
  return String(line)
    .replace(/^\s*[-•*]\s+/, '')
    .replace(/^\s*\d+[.)]\s+/, '')
    .trim()
}

export function normalizeCommanderActionLine(line, maxLen = 34) {
  if (!line || typeof line !== 'string') return ''
  let s = line
    .replace(/^\s*(建议|推荐|可考虑|可以|请|应当|应|需)\s*[:：]?\s*/g, '')
    .replace(/^[\s-•*]+/g, '')
    .trim()

  // Remove trailing punctuation
  s = s.replace(/[。；;\s]+$/g, '').trim()
  if (!s) return ''

  // Clamp length for a “telegraph” feel
  if (typeof maxLen === 'number' && maxLen > 10 && s.length > maxLen) {
    s = s.slice(0, maxLen).trim() + '…'
  }
  return s
}

function _splitToActionItems(text) {
  const raw = String(text || '').trim()
  if (!raw) return []

  // First pass: split by strong separators.
  let parts = raw
    .split(/(?:；|\n|\r\n|。)+/)
    .map((s) => s.trim())
    .filter(Boolean)

  // Second pass: if still a single long sentence, try soft split.
  if (parts.length <= 1 && raw.length >= 28) {
    parts = raw
      .split(/，(?=并|同时|结合|对|将|优先)/)
      .map((s) => s.trim())
      .filter(Boolean)
  }

  return parts
    .map((s) => s.replace(/[。；\s]+$/g, '').trim())
    .filter(Boolean)
}

// Extract 1–2 actionable recommendation bullets from backend /api/report text.
// Preference order:
// 1) Markdown/numbered bullets
// 2) A "建议：..." line/section
export function extractActionInsightsFromReport(reportText, maxItems = 2) {
  if (!reportText || typeof reportText !== 'string') return []
  const text = reportText.replace(/\r\n/g, '\n').trim()
  if (!text) return []

  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)

  // 0) Prefer bracket-tag action lines in playbook style.
  // Examples: [行动建议] ... / [治理干预] ... / [勘测指令] ... / [协同联动] ...
  const tagged = lines
    .filter((l) => /^\[(行动建议|治理干预|勘测指令|协同联动|决策支持|快速响应)\]/.test(l))
    .map((l) => l.replace(/^\[[^\]]+\]\s*/, '').trim())
    .map((s) => normalizeCommanderActionLine(s))
    .filter(Boolean)
  if (tagged.length) return tagged.slice(0, Math.max(1, maxItems))

  // 1) Bullet lines (LLM may output these)
  const bulletLines = lines
    .filter((l) => /^([-•*]\s+|\d+[.)]\s+)/.test(l))
    .map(_stripBulletPrefix)
    .filter(Boolean)

  if (bulletLines.length) {
    return bulletLines
      .map((s) => normalizeCommanderActionLine(s))
      .filter(Boolean)
      .slice(0, Math.max(1, maxItems))
  }

  // 2) "建议：" inline
  const inline = text.match(/建议\s*[:：]\s*([^\n]+)/)
  if (inline && inline[1]) {
    const items = _splitToActionItems(inline[1])
      .map((s) => normalizeCommanderActionLine(s))
      .filter(Boolean)
    if (items.length) return items.slice(0, Math.max(1, maxItems))
  }

  // 3) "建议：" section (until next bracket header or end)
  const section = text.match(/建议\s*[:：]\s*([\s\S]+?)\n(?=【|\S+[:：])|建议\s*[:：]\s*([\s\S]+)$/)
  const sectionText = (section && (section[1] || section[2])) ? String(section[1] || section[2]).trim() : ''
  if (sectionText) {
    const items = _splitToActionItems(sectionText)
      .map((s) => normalizeCommanderActionLine(s))
      .filter(Boolean)
    if (items.length) return items.slice(0, Math.max(1, maxItems))
  }

  return []
}

// Build a short, single-line reading hint from legends, e.g.
// "判读：蓝=扩张/恢复；橙红=退缩/淤积"
export function buildLegendHint(legends, maxPairs = 2, maxLen = 68) {
  if (!Array.isArray(legends) || legends.length === 0) return ''

  const pairs = []
  for (const l of legends) {
    const label = String(l?.label || '').trim()
    if (!label) continue
    const m = label.match(/^(.{1,16}?)[：:]\s*(.+)$/)
    if (!m) continue

    let key = String(m[1] || '').trim()
    let val = String(m[2] || '').trim()

    key = key
      .replace(/(区域|斑块|高亮|暗影)$/g, '')
      .replace(/\s+/g, ' ')
      .trim()
    if (key.length > 10) key = key.slice(0, 10).trim()

    val = val.replace(/[。；;\s]+$/g, '').trim()
    if (!key || !val) continue

    pairs.push(`${key}=${val}`)
    if (pairs.length >= Math.max(1, maxPairs)) break
  }

  if (!pairs.length) return ''

  let s = `判读：${pairs.join('；')}`
  if (typeof maxLen === 'number' && maxLen > 24 && s.length > maxLen) {
    s = s.slice(0, maxLen).trim() + '…'
  }
  return s
}
