<template>
  <div class="insar-ts-card" :class="riskThemeClass">
    <!-- Header with target & risk level -->
    <div class="ts-header">
      <div class="ts-title-group">
        <span class="ts-pulse-dot" :class="riskLevel"></span>
        <div class="ts-target-info">
          <div class="ts-target-name">{{ data?.target_name || 'InSAR 靶向时序沉降体检' }}</div>
          <div class="ts-coords" v-if="data?.lat && data?.lon">
            {{ formatCoords(data.lat, data.lon) }} · 相干性 γ={{ (data.coherence || 0).toFixed(2) }}
          </div>
        </div>
      </div>
      <div class="ts-badge" :class="riskLevel">
        {{ data?.risk_label || '监测中' }}
      </div>
    </div>

    <!-- Key Metrics Ribbon -->
    <div class="ts-metrics-grid">
      <div class="metric-item">
        <span class="m-label">年均沉降速率</span>
        <span class="m-value velocity" :class="velocityColorClass">
          {{ formatNumber(data?.velocity_mm_yr) }} mm/yr
        </span>
      </div>
      <div class="metric-item">
        <span class="m-label">5年最大累积形变</span>
        <span class="m-value cumu" :class="cumuColorClass">
          {{ formatNumber(data?.cumulative_displacement_mm) }} mm
        </span>
      </div>
      <div class="metric-item">
        <span class="m-label">形变力学机理</span>
        <span class="m-value mech" :title="data?.deformation_type">
          {{ truncate(data?.deformation_type, 14) }}
        </span>
      </div>
    </div>

    <!-- SVG Time-Series Chart -->
    <div class="ts-chart-container" ref="chartContainer">
      <svg
        v-if="chartPoints.length"
        class="ts-svg"
        viewBox="0 0 380 140"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="curveGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#00f5ff" stop-opacity="0.9" />
            <stop offset="60%" stop-color="#ffd000" stop-opacity="0.8" />
            <stop offset="100%" stop-color="#ff3b30" stop-opacity="0.95" />
          </linearGradient>
          <linearGradient id="areaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#00f5ff" stop-opacity="0.25" />
            <stop offset="100%" stop-color="#ff3b30" stop-opacity="0.02" />
          </linearGradient>
        </defs>

        <!-- Grid Lines -->
        <line x1="30" y1="20" x2="370" y2="20" class="chart-grid" />
        <line x1="30" y1="65" x2="370" y2="65" class="chart-grid" />
        <line x1="30" y1="110" x2="370" y2="110" class="chart-grid" />

        <!-- High-Risk -20mm Threshold Line -->
        <line
          v-if="riskLineY !== null"
          x1="30"
          :y1="riskLineY"
          x2="370"
          :y2="riskLineY"
          class="risk-threshold-line"
        />
        <text
          v-if="riskLineY !== null"
          x="368"
          :y="riskLineY - 3"
          class="risk-threshold-label"
        >
          -20mm 高危警戒
        </text>

        <!-- Zero Baseline -->
        <line
          v-if="zeroLineY !== null"
          x1="30"
          :y1="zeroLineY"
          x2="370"
          :y2="zeroLineY"
          class="zero-baseline"
        />
        <text
          v-if="zeroLineY !== null"
          x="28"
          :y="zeroLineY + 3"
          class="axis-label zero"
        >
          0
        </text>

        <!-- Area Fill -->
        <polygon :points="areaPolygonPoints" fill="url(#areaGrad)" />

        <!-- Displacement Curve Path -->
        <path :d="curvePathD" class="curve-stroke" />

        <!-- Data Point Circles -->
        <g v-for="(pt, idx) in chartPoints" :key="idx">
          <circle
            :cx="pt.x"
            :cy="pt.y"
            r="4"
            class="pt-circle"
            :class="{ active: hoveredIndex === idx }"
            @mouseenter="hoveredIndex = idx"
            @mouseleave="hoveredIndex = null"
          />
        </g>
      </svg>

      <!-- Hover Tooltip -->
      <div
        v-if="hoveredPoint"
        class="chart-tooltip"
        :style="{ left: `${hoveredPoint.leftPercent}%`, top: `${hoveredPoint.topPx}px` }"
      >
        <div class="tt-date">{{ hoveredPoint.epoch }}</div>
        <div class="tt-val">{{ hoveredPoint.disp }} mm</div>
      </div>

      <!-- X-Axis Epoch Labels -->
      <div class="x-axis-labels">
        <span v-for="(ep, idx) in shortEpochs" :key="idx" class="epoch-label">
          {{ ep }}
        </span>
      </div>
    </div>

    <!-- AEF Semantic & Recommendations -->
    <div class="ts-footer">
      <div class="aef-tag-line">
        <span class="aef-badge">AEF 语义融合</span>
        <span class="aef-text">{{ data?.aef_semantic || '人造物硬化面分析' }}</span>
      </div>
      <div v-if="data?.recommendations" class="rec-box">
        <span class="rec-icon">🛡️</span>
        <span class="rec-text">{{ data.recommendations }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'

export default {
  name: 'InsarTimeseriesChart',
  props: {
    data: {
      type: Object,
      default: () => null
    }
  },
  setup(props) {
    const hoveredIndex = ref(null)

    const riskLevel = computed(() => props.data?.risk_level || 'safe')
    const riskThemeClass = computed(() => `theme-${riskLevel.value}`)

    const velocityColorClass = computed(() => {
      const v = props.data?.velocity_mm_yr || 0
      if (v < -20) return 'text-red'
      if (v < -8) return 'text-orange'
      return 'text-green'
    })

    const cumuColorClass = computed(() => {
      const c = props.data?.cumulative_displacement_mm || 0
      if (c < -40) return 'text-red'
      if (c < -15) return 'text-orange'
      return 'text-green'
    })

    // Coordinate chart normalization (viewBox 380x140)
    // Left padding: 35, Right padding: 370. Width = 335.
    // Top padding: 20, Bottom padding: 115. Height = 95.
    const chartMetrics = computed(() => {
      const disps = props.data?.displacements_mm || []
      if (!disps.length) return null

      const minVal = Math.min(...disps, -25.0)
      const maxVal = Math.max(...disps, 2.0)
      const range = (maxVal - minVal) || 1

      const xStart = 35
      const xEnd = 365
      const yTop = 20
      const yBottom = 115
      const xStep = disps.length > 1 ? (xEnd - xStart) / (disps.length - 1) : 0

      return { minVal, maxVal, range, xStart, xEnd, yTop, yBottom, xStep }
    })

    const chartPoints = computed(() => {
      const m = chartMetrics.value
      const disps = props.data?.displacements_mm || []
      const epochs = props.data?.epochs || []
      if (!m || !disps.length) return []

      return disps.map((val, i) => {
        const x = m.xStart + i * m.xStep
        const norm = (val - m.minVal) / m.range // 0 (minVal) to 1 (maxVal)
        const y = m.yBottom - norm * (m.yBottom - m.yTop)
        return {
          x: Math.round(x * 10) / 10,
          y: Math.round(y * 10) / 10,
          disp: val,
          epoch: epochs[i] || `Phase ${i + 1}`,
          leftPercent: Math.round((x / 380) * 100),
          topPx: Math.max(10, Math.min(100, Math.round(y)))
        }
      })
    })

    const curvePathD = computed(() => {
      const pts = chartPoints.value
      if (!pts.length) return ''
      return pts.reduce((acc, pt, i) => {
        if (i === 0) return `M ${pt.x} ${pt.y}`
        // Smooth bezier interpolation
        const prev = pts[i - 1]
        const cx1 = (prev.x + pt.x) / 2
        const cy1 = prev.y
        const cx2 = (prev.x + pt.x) / 2
        const cy2 = pt.y
        return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${pt.x} ${pt.y}`
      }, '')
    })

    const areaPolygonPoints = computed(() => {
      const pts = chartPoints.value
      const m = chartMetrics.value
      if (!pts.length || !m) return ''
      const first = pts[0]
      const last = pts[pts.length - 1]
      const ptsStr = pts.map(p => `${p.x},${p.y}`).join(' ')
      return `${first.x},${m.yBottom} ${ptsStr} ${last.x},${m.yBottom}`
    })

    const riskLineY = computed(() => {
      const m = chartMetrics.value
      if (!m) return null
      const val = -20.0
      if (val < m.minVal || val > m.maxVal) return null
      const norm = (val - m.minVal) / m.range
      return Math.round((m.yBottom - norm * (m.yBottom - m.yTop)) * 10) / 10
    })

    const zeroLineY = computed(() => {
      const m = chartMetrics.value
      if (!m) return null
      const val = 0.0
      if (val < m.minVal || val > m.maxVal) return null
      const norm = (val - m.minVal) / m.range
      return Math.round((m.yBottom - norm * (m.yBottom - m.yTop)) * 10) / 10
    })

    const shortEpochs = computed(() => {
      const eps = props.data?.epochs || []
      // Return 5 evenly spaced labels
      if (!eps.length) return []
      if (eps.length <= 5) return eps.map(e => e.slice(2, 7))
      return [
        eps[0]?.slice(2, 7),
        eps[Math.floor(eps.length * 0.25)]?.slice(2, 7),
        eps[Math.floor(eps.length * 0.5)]?.slice(2, 7),
        eps[Math.floor(eps.length * 0.75)]?.slice(2, 7),
        eps[eps.length - 1]?.slice(2, 7)
      ]
    })

    const hoveredPoint = computed(() => {
      if (hoveredIndex.value === null) return null
      return chartPoints.value[hoveredIndex.value] || null
    })

    function formatCoords(lat, lon) {
      if (lat === undefined || lon === undefined) return ''
      return `${Number(lat).toFixed(3)}°N, ${Number(lon).toFixed(3)}°E`
    }

    function formatNumber(v) {
      if (v === undefined || v === null) return '—'
      const num = Number(v)
      return (num > 0 ? `+${num.toFixed(1)}` : num.toFixed(1))
    }

    function truncate(str, len) {
      if (!str) return '—'
      return str.length > len ? str.slice(0, len) + '…' : str
    }

    return {
      riskLevel,
      riskThemeClass,
      velocityColorClass,
      cumuColorClass,
      chartPoints,
      curvePathD,
      areaPolygonPoints,
      riskLineY,
      zeroLineY,
      shortEpochs,
      hoveredIndex,
      hoveredPoint,
      formatCoords,
      formatNumber,
      truncate
    }
  }
}
</script>

<style scoped>
.insar-ts-card {
  border-radius: 12px;
  background: rgba(8, 14, 24, 0.92);
  border: 1px solid rgba(0, 245, 255, 0.28);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  padding: 12px 14px;
  color: #fff;
  backdrop-filter: blur(16px);
  margin-top: 10px;
}

.insar-ts-card.theme-critical {
  border-color: rgba(255, 59, 48, 0.45);
  box-shadow: 0 10px 30px rgba(255, 59, 48, 0.15), inset 0 1px 0 rgba(255, 59, 48, 0.2);
}

.insar-ts-card.theme-warning {
  border-color: rgba(255, 149, 0, 0.45);
  box-shadow: 0 10px 30px rgba(255, 149, 0, 0.15), inset 0 1px 0 rgba(255, 149, 0, 0.2);
}

/* Header */
.ts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.ts-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ts-pulse-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #00f5ff;
  box-shadow: 0 0 10px #00f5ff;
}

.ts-pulse-dot.critical {
  background: #ff3b30;
  box-shadow: 0 0 12px #ff3b30;
  animation: blink-dot 1.5s infinite ease-in-out;
}

.ts-pulse-dot.warning {
  background: #ff9500;
  box-shadow: 0 0 10px #ff9500;
}

@keyframes blink-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

.ts-target-name {
  font-size: 13px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.3px;
}

.ts-coords {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 1px;
}

.ts-badge {
  font-size: 10px;
  font-weight: 900;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid rgba(0, 245, 255, 0.3);
  background: rgba(0, 245, 255, 0.12);
  color: #00f5ff;
  white-space: nowrap;
}

.ts-badge.critical {
  border-color: rgba(255, 59, 48, 0.4);
  background: rgba(255, 59, 48, 0.18);
  color: #ff5247;
}

.ts-badge.warning {
  border-color: rgba(255, 149, 0, 0.4);
  background: rgba(255, 149, 0, 0.18);
  color: #ffaa33;
}

/* Metrics Ribbon */
.ts-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: rgba(0, 0, 0, 0.32);
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 10px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.m-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 700;
}

.m-value {
  font-size: 13px;
  font-weight: 900;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.text-red { color: #ff3b30; }
.text-orange { color: #ff9500; }
.text-green { color: #00ff9d; }

.m-value.mech {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.88);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* SVG Chart */
.ts-chart-container {
  position: relative;
  width: 100%;
  height: 140px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 18px;
}

.ts-svg {
  width: 100%;
  height: 120px;
  overflow: visible;
}

.chart-grid {
  stroke: rgba(255, 255, 255, 0.08);
  stroke-dasharray: 3 3;
  stroke-width: 1;
}

.risk-threshold-line {
  stroke: rgba(255, 59, 48, 0.65);
  stroke-dasharray: 4 3;
  stroke-width: 1.2;
}

.risk-threshold-label {
  fill: #ff5247;
  font-size: 9px;
  font-weight: 800;
  text-anchor: end;
}

.zero-baseline {
  stroke: rgba(255, 255, 255, 0.25);
  stroke-width: 1;
}

.axis-label {
  fill: rgba(255, 255, 255, 0.4);
  font-size: 9px;
  text-anchor: end;
}

.curve-stroke {
  fill: none;
  stroke: url(#curveGrad);
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 6px rgba(0, 245, 255, 0.4));
}

.pt-circle {
  fill: #080e18;
  stroke: #00f5ff;
  stroke-width: 2;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pt-circle:hover,
.pt-circle.active {
  r: 6;
  fill: #00f5ff;
  stroke: #ffffff;
  stroke-width: 2.5;
  filter: drop-shadow(0 0 8px rgba(0, 245, 255, 0.8));
}

.chart-tooltip {
  position: absolute;
  transform: translate(-50%, -100%);
  background: rgba(10, 18, 30, 0.95);
  border: 1px solid rgba(0, 245, 255, 0.45);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.7);
  padding: 4px 8px;
  border-radius: 6px;
  pointer-events: none;
  z-index: 10;
  text-align: center;
  white-space: nowrap;
}

.tt-date {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.6);
}

.tt-val {
  font-size: 11px;
  font-weight: 900;
  color: #00f5ff;
  font-family: ui-monospace, monospace;
}

.x-axis-labels {
  position: absolute;
  bottom: 3px;
  left: 30px;
  right: 15px;
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.45);
  font-family: ui-monospace, monospace;
}

/* Footer & Recommendations */
.ts-footer {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.aef-tag-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.aef-badge {
  font-size: 9px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0, 255, 157, 0.15);
  border: 1px solid rgba(0, 255, 157, 0.35);
  color: #00ff9d;
}

.aef-text {
  color: rgba(255, 255, 255, 0.75);
}

.rec-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 180, 0, 0.08);
  border: 1px dashed rgba(255, 180, 0, 0.3);
  font-size: 11px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.88);
}

.rec-icon {
  font-size: 12px;
  flex-shrink: 0;
}
</style>
