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

    <!-- 2D Vector & Kinematic Metrics Ribbon (Dual Metric Scales) -->
    <div class="ts-metrics-grid">
      <div class="metric-item">
        <span class="m-label">年均沉降速率 (标尺 -20mm/yr)</span>
        <span class="m-value velocity" :class="velocityColorClass">
          {{ formatNumber(data?.vertical_velocity_mm_yr ?? data?.velocity_mm_yr) }} mm/yr
        </span>
      </div>
      <div class="metric-item">
        <span class="m-label">5年累积沉降 (限值 {{ data?.cumulative_threshold_mm ?? -30 }}mm)</span>
        <span class="m-value cumu" :class="cumuColorClass">
          {{ formatNumber(data?.cumulative_displacement_mm) }} mm
        </span>
      </div>
      <div class="metric-item">
        <span class="m-label">东西向侧移 / 弹性幅</span>
        <span class="m-value lateral" :class="lateralColorClass">
          {{ formatNumber(data?.lateral_velocity_mm_yr) }} mm/yr (±{{ (data?.elastic_amplitude_mm ?? 1.2).toFixed(1) }}mm)
        </span>
      </div>
    </div>

    <!-- Component Curve Selector Tabs (Rate vs Cumulative vs Components) -->
    <div class="ts-curve-tabs">
      <button
        class="tab-btn"
        :class="{ active: activeMode === 'total' }"
        @click="activeMode = 'total'"
        title="5年实测累积位移历程 (含塑性固结与温变波动)"
      >
        累积总形变
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeMode === 'trend' }"
        @click="activeMode = 'trend'"
        title="剥离可逆温变后的真实力学塑性沉降趋势"
      >
        塑性趋势项
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeMode === 'seasonal' }"
        @click="activeMode = 'seasonal'"
        title="气温热胀冷缩与丰枯水期孔压弹性呼吸波动"
      >
        温变弹性项
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeMode === 'rate' }"
        @click="activeMode = 'rate'"
        title="各期区间年化沉降速率对比 (-20mm/yr 警戒线)"
      >
        年化沉降速率
      </button>
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
            <stop offset="0%" stop-color="#00f5ff" stop-opacity="0.95" />
            <stop offset="60%" stop-color="#ffd000" stop-opacity="0.85" />
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

        <!-- 1. Cumulative Mode: Dynamic Rate Envelope Slope Line (-20mm/yr * t) -->
        <g v-if="activeMode !== 'seasonal' && activeMode !== 'rate' && rateSlopeLine">
          <line
            :x1="rateSlopeLine.x1"
            :y1="rateSlopeLine.y1"
            :x2="rateSlopeLine.x2"
            :y2="rateSlopeLine.y2"
            class="rate-slope-line"
          />
          <text
            :x="rateSlopeLine.x2 - 4"
            :y="rateSlopeLine.y2 - 4"
            class="rate-slope-label"
          >
            -20mm/yr 速率斜率包络
          </text>
        </g>

        <!-- 2. Cumulative Mode: Structural Allowable Total Settlement Limit Line -->
        <g v-if="activeMode !== 'seasonal' && activeMode !== 'rate' && cumulativeLineY !== null">
          <line
            x1="30"
            :y1="cumulativeLineY"
            x2="370"
            :y2="cumulativeLineY"
            class="cumu-threshold-line"
          />
          <text
            x="368"
            :y="cumulativeLineY - 3"
            class="cumu-threshold-label"
          >
            {{ data?.cumulative_threshold_label || '允许累积沉降上限' }}
          </text>
        </g>

        <!-- 3. Rate Mode: Horizontal -20mm/yr Annualized Rate Limit Line -->
        <g v-if="activeMode === 'rate' && rateLineY !== null">
          <line
            x1="30"
            :y1="rateLineY"
            x2="370"
            :y2="rateLineY"
            class="rate-threshold-line"
          />
          <text
            x="368"
            :y="rateLineY - 3"
            class="rate-threshold-label"
          >
            -20 mm/yr 行业年均速率高危控制线
          </text>
        </g>

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

        <!-- Displacement / Velocity Curve Path -->
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
        <div class="tt-val">{{ hoveredPoint.disp }} {{ activeMode === 'rate' ? 'mm/yr' : 'mm' }}</div>
      </div>

      <!-- X-Axis Epoch Labels -->
      <div class="x-axis-labels">
        <span v-for="(ep, idx) in shortEpochs" :key="idx" class="epoch-label">
          {{ ep }}
        </span>
      </div>
    </div>

    <!-- Dual Physical Metric Clarification -->
    <div class="dual-standard-tip">
      <span class="tip-icon">⚖️</span>
      <span class="tip-text">
        <strong>工程双物理标尺提示：</strong>沉降速率（mm/yr）与 5 年累积沉降（mm）解耦分别对应独立控制线，彻底避免多年累积量与单年速率控制线误混。
      </span>
    </div>

    <!-- AEF Semantic & Multi-modal Diagnostics -->
    <div class="ts-footer">
      <div class="aef-tag-line">
        <span class="aef-badge">AEF 语义多模态</span>
        <span class="aef-text">{{ data?.aef_semantic || '人造物硬化面分析' }}</span>
      </div>

      <!-- 2D Lateral Ground Spread / Pit Wall Diagnostic -->
      <div v-if="data?.lateral_displacement_type" class="lateral-box">
        <span class="lat-icon">📐</span>
        <div class="lat-content">
          <div class="lat-title">{{ data.lateral_displacement_type }}</div>
          <div class="lat-diag">{{ data.lateral_risk_diagnostic }}</div>
        </div>
      </div>

      <!-- Engineering Recommendations -->
      <div v-if="data?.recommendations" class="rec-box">
        <span class="rec-icon">🛡️</span>
        <span class="rec-text">{{ data.recommendations }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'
import {
  evaluateRiskLevel,
  projectTimeseriesPoints,
  buildSmoothCurvePath,
  buildAreaPolygonPoints,
  formatCoordinates,
  formatDeformationRate,
  extractCurveSeries
} from '../utils/insarTimeseries.js'

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
    const activeMode = ref('total') // 'total' | 'trend' | 'seasonal' | 'rate'

    const riskEval = computed(() => {
      const v = props.data?.velocity_mm_yr || 0
      const c = props.data?.cumulative_displacement_mm || 0
      return evaluateRiskLevel(v, c)
    })

    const riskLevel = computed(() => props.data?.risk_level || riskEval.value.level)
    const riskThemeClass = computed(() => `theme-${riskLevel.value}`)

    const velocityColorClass = computed(() => {
      const v = props.data?.vertical_velocity_mm_yr ?? props.data?.velocity_mm_yr ?? 0
      if (v < -20) return 'text-red'
      if (v < -8) return 'text-orange'
      return 'text-green'
    })

    const cumuColorClass = computed(() => {
      const c = props.data?.cumulative_displacement_mm || 0
      const limit = props.data?.cumulative_threshold_mm || -30.0
      if (c < limit) return 'text-red'
      if (c < limit * 0.5) return 'text-orange'
      return 'text-green'
    })

    const lateralColorClass = computed(() => {
      const lv = Math.abs(props.data?.lateral_velocity_mm_yr || 0)
      if (lv > 5) return 'text-orange'
      if (lv > 1) return 'text-cyan'
      return 'text-green'
    })

    const activeSeries = computed(() => {
      return extractCurveSeries(props.data, activeMode.value)
    })

    const chartProjection = computed(() => {
      const disps = activeSeries.value
      const epochs = props.data?.epochs || []
      const cumuThresh = props.data?.cumulative_threshold_mm ?? -30.0
      return projectTimeseriesPoints(disps, epochs, {
        cumulativeThresholdVal: cumuThresh,
        rateEnvelopeSlope: -20.0
      })
    })

    const chartPoints = computed(() => chartProjection.value.points)
    const cumulativeLineY = computed(() => chartProjection.value.cumulativeLineY)
    const rateLineY = computed(() => chartProjection.value.rateLineY)
    const rateSlopeLine = computed(() => chartProjection.value.rateSlopeLine)
    const zeroLineY = computed(() => chartProjection.value.zeroLineY)

    const curvePathD = computed(() => {
      return buildSmoothCurvePath(chartPoints.value)
    })

    const areaPolygonPoints = computed(() => {
      return buildAreaPolygonPoints(chartPoints.value, 115)
    })

    const shortEpochs = computed(() => {
      const eps = props.data?.epochs || []
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
      return formatCoordinates(lat, lon)
    }

    function formatNumber(v) {
      return formatDeformationRate(v)
    }

    return {
      activeMode,
      riskLevel,
      riskThemeClass,
      velocityColorClass,
      cumuColorClass,
      lateralColorClass,
      chartPoints,
      curvePathD,
      areaPolygonPoints,
      cumulativeLineY,
      rateLineY,
      rateSlopeLine,
      zeroLineY,
      shortEpochs,
      hoveredIndex,
      hoveredPoint,
      formatCoords,
      formatNumber
    }
  }
}
</script>

<style scoped>
.insar-ts-card {
  border-radius: 12px;
  background: rgba(8, 14, 24, 0.94);
  border: 1px solid rgba(0, 245, 255, 0.28);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.1);
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
  margin-bottom: 8px;
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

/* 2D Vector Metrics Ribbon */
.ts-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: rgba(0, 0, 0, 0.35);
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 8px;
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
.text-cyan { color: #00f5ff; }

/* Curve Mode Selector Tabs */
.ts-curve-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}

.tab-btn {
  padding: 3px 7px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.09);
  color: #fff;
}

.tab-btn.active {
  background: rgba(0, 245, 255, 0.16);
  border-color: rgba(0, 245, 255, 0.45);
  color: #00f5ff;
  box-shadow: 0 0 8px rgba(0, 245, 255, 0.2);
}

/* SVG Chart */
.ts-chart-container {
  position: relative;
  width: 100%;
  height: 140px;
  background: rgba(0, 0, 0, 0.28);
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

/* Rate slope envelope */
.rate-slope-line {
  stroke: rgba(255, 208, 0, 0.65);
  stroke-dasharray: 3 2;
  stroke-width: 1.2;
}

.rate-slope-label {
  fill: #ffd000;
  font-size: 8px;
  font-weight: 700;
  text-anchor: end;
}

/* Structural cumulative line */
.cumu-threshold-line {
  stroke: rgba(255, 59, 48, 0.7);
  stroke-dasharray: 4 3;
  stroke-width: 1.3;
}

.cumu-threshold-label {
  fill: #ff5247;
  font-size: 8.5px;
  font-weight: 800;
  text-anchor: end;
}

/* Rate horizontal line */
.rate-threshold-line {
  stroke: rgba(255, 59, 48, 0.85);
  stroke-dasharray: 4 3;
  stroke-width: 1.4;
}

.rate-threshold-label {
  fill: #ff5247;
  font-size: 8.5px;
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

/* Dual Metric Clarification Tip */
.dual-standard-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.15);
  font-size: 10px;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.78);
}

.tip-icon {
  font-size: 11px;
  flex-shrink: 0;
}

/* Footer & Recommendations */
.ts-footer {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 5px;
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

.lateral-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(0, 245, 255, 0.07);
  border: 1px dashed rgba(0, 245, 255, 0.28);
  font-size: 10.5px;
  line-height: 1.35;
}

.lat-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.lat-title {
  font-weight: 800;
  color: #00f5ff;
}

.lat-diag {
  color: rgba(255, 255, 255, 0.8);
  margin-top: 1px;
}

.rec-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(255, 180, 0, 0.08);
  border: 1px dashed rgba(255, 180, 0, 0.3);
  font-size: 10.5px;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.88);
}

.rec-icon {
  font-size: 12px;
  flex-shrink: 0;
}
</style>
