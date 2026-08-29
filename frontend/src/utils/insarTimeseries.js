/**
 * InSAR Time-Series displacement analysis and SVG chart projection utilities.
 */

/**
 * Evaluates the engineering risk level and risk badge based on deformation velocity and cumulative displacement.
 * @param {number} velocity 年均形变速率 (mm/yr)
 * @param {number} cumulativeDisp 最大累积形变量 (mm)
 * @returns {{ level: 'safe'|'warning'|'critical', label: string, colorClass: string }}
 */
export function evaluateRiskLevel(velocity, cumulativeDisp = 0) {
  const v = Number(velocity || 0)
  const c = Number(cumulativeDisp || 0)

  if (v < -20.0 || c < -50.0) {
    return {
      level: 'critical',
      label: '严重沉降高危 (Critical)',
      colorClass: 'text-red'
    }
  }
  if (v < -8.0 || c < -20.0) {
    return {
      level: 'warning',
      label: '显著形变关注 (Warning)',
      colorClass: 'text-orange'
    }
  }
  return {
    level: 'safe',
    label: '地表基本稳定 (Safe)',
    colorClass: 'text-green'
  }
}

/**
 * Projects displacement time-series points onto SVG canvas coordinate space.
 * @param {number[]} displacements 累积位移数组 (mm)
 * @param {string[]} epochs 观测日期时相
 * @param {Object} [options]
 * @param {number} [options.width=380]
 * @param {number} [options.height=140]
 * @returns {{ points: Array<{ x: number, y: number, disp: number, epoch: string }>, riskLineY: number|null, zeroLineY: number|null, minVal: number, maxVal: number }}
 */
export function projectTimeseriesPoints(displacements, epochs = [], options = {}) {
  if (!Array.isArray(displacements) || !displacements.length) {
    return { points: [], riskLineY: null, zeroLineY: null, minVal: 0, maxVal: 0 }
  }

  const xStart = options.xStart ?? 35
  const xEnd = options.xEnd ?? 365
  const yTop = options.yTop ?? 20
  const yBottom = options.yBottom ?? 115

  const minVal = Math.min(...displacements, -25.0)
  const maxVal = Math.max(...displacements, 2.0)
  const range = (maxVal - minVal) || 1

  const xStep = displacements.length > 1 ? (xEnd - xStart) / (displacements.length - 1) : 0

  const points = displacements.map((val, i) => {
    const x = xStart + i * xStep
    const norm = (val - minVal) / range
    const y = yBottom - norm * (yBottom - yTop)
    return {
      x: Math.round(x * 10) / 10,
      y: Math.round(y * 10) / 10,
      disp: val,
      epoch: epochs[i] || `Phase ${i + 1}`,
      leftPercent: Math.round((x / 380) * 100),
      topPx: Math.max(10, Math.min(100, Math.round(y)))
    }
  })

  // Risk line at -20mm
  let riskLineY = null
  if (-20.0 >= minVal && -20.0 <= maxVal) {
    const normRisk = (-20.0 - minVal) / range
    riskLineY = Math.round((yBottom - normRisk * (yBottom - yTop)) * 10) / 10
  }

  // Zero baseline at 0mm
  let zeroLineY = null
  if (0.0 >= minVal && 0.0 <= maxVal) {
    const normZero = (0.0 - minVal) / range
    zeroLineY = Math.round((yBottom - normZero * (yBottom - yTop)) * 10) / 10
  }

  return { points, riskLineY, zeroLineY, minVal, maxVal }
}

/**
 * Builds SVG smooth Bezier curve path string from projected points.
 * @param {Array<{ x: number, y: number }>} points
 * @returns {string}
 */
export function buildSmoothCurvePath(points) {
  if (!Array.isArray(points) || !points.length) return ''
  return points.reduce((acc, pt, i) => {
    if (i === 0) return `M ${pt.x} ${pt.y}`
    const prev = points[i - 1]
    const cx1 = (prev.x + pt.x) / 2
    const cy1 = prev.y
    const cx2 = (prev.x + pt.x) / 2
    const cy2 = pt.y
    return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${pt.x} ${pt.y}`
  }, '')
}

/**
 * Builds SVG area polygon points string.
 * @param {Array<{ x: number, y: number }>} points
 * @param {number} [bottomY=115]
 * @returns {string}
 */
export function buildAreaPolygonPoints(points, bottomY = 115) {
  if (!Array.isArray(points) || !points.length) return ''
  const first = points[0]
  const last = points[points.length - 1]
  const ptsStr = points.map(p => `${p.x},${p.y}`).join(' ')
  return `${first.x},${bottomY} ${ptsStr} ${last.x},${bottomY}`
}

/**
 * Formats coordinates into standard geographical string.
 * @param {number} lat
 * @param {number} lon
 * @returns {string}
 */
export function formatCoordinates(lat, lon) {
  if (lat === undefined || lon === undefined || lat === null || lon === null) return ''
  return `${Number(lat).toFixed(3)}°N, ${Number(lon).toFixed(3)}°E`
}
