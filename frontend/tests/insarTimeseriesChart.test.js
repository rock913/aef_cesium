import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import {
  evaluateRiskLevel,
  projectTimeseriesPoints,
  buildSmoothCurvePath,
  buildAreaPolygonPoints,
  formatCoordinates,
  formatDeformationRate,
  extractCurveSeries
} from '../src/utils/insarTimeseries.js'

function readAppVue() {
  const p = path.resolve(__dirname, '../src/App.vue')
  return fs.readFileSync(p, 'utf-8')
}

function readChartVue() {
  const p = path.resolve(__dirname, '../src/components/InsarTimeseriesChart.vue')
  return fs.readFileSync(p, 'utf-8')
}

function readCesiumViewerVue() {
  const p = path.resolve(__dirname, '../src/components/CesiumViewer.vue')
  return fs.readFileSync(p, 'utf-8')
}

describe('InSAR Time-Series Mathematical & Risk Evaluation Logic', () => {
  const sampleDisps = [-2.1, -6.5, -11.8, -17.2, -23.0, -28.4, -33.9, -39.1, -44.5, -50.2]
  const sampleEpochs = [
    '2020-03-15', '2020-09-15',
    '2021-03-15', '2021-09-15',
    '2022-03-15', '2022-09-15',
    '2023-03-15', '2023-09-15',
    '2024-03-15', '2024-09-15'
  ]

  it('correctly evaluates critical risk level for rapid subsidence', () => {
    const r1 = evaluateRiskLevel(-24.5, -50.2)
    expect(r1.level).toBe('critical')
    expect(r1.label).toContain('严重沉降高危')
    expect(r1.colorClass).toBe('text-red')

    const r2 = evaluateRiskLevel(-12.0, -18.5)
    expect(r2.level).toBe('warning')
    expect(r2.label).toContain('显著形变关注')
    expect(r2.colorClass).toBe('text-orange')

    const r3 = evaluateRiskLevel(-0.8, -3.2)
    expect(r3.level).toBe('safe')
    expect(r3.label).toContain('地表基本稳定')
    expect(r3.colorClass).toBe('text-green')
  })

  it('projects displacement points onto SVG canvas coordinate space', () => {
    const res = projectTimeseriesPoints(sampleDisps, sampleEpochs)
    expect(res.points).toHaveLength(10)
    expect(res.points[0].disp).toBe(-2.1)
    expect(res.points[9].disp).toBe(-50.2)
    expect(res.points[0].epoch).toBe('2020-03-15')

    // Points monotonically advance along X
    for (let i = 1; i < res.points.length; i++) {
      expect(res.points[i].x).toBeGreaterThan(res.points[i - 1].x)
    }

    // High risk line at -20mm is present
    expect(res.riskLineY).not.toBeNull()
    expect(typeof res.riskLineY).toBe('number')
  })

  it('builds SVG smooth bezier curves and area polygons', () => {
    const res = projectTimeseriesPoints(sampleDisps, sampleEpochs)
    const curve = buildSmoothCurvePath(res.points)
    expect(curve.startsWith('M ')).toBe(true)
    expect(curve).toContain('C ')

    const area = buildAreaPolygonPoints(res.points, 115)
    expect(typeof area).toBe('string')
    expect(area.length).toBeGreaterThan(20)
  })

  it('formats geographical coordinates and rates nicely', () => {
    expect(formatCoordinates(22.72, 113.53)).toBe('22.720°N, 113.530°E')
    expect(formatCoordinates(null, null)).toBe('')
    expect(formatDeformationRate(-26.5)).toBe('-26.5')
    expect(formatDeformationRate(6.8)).toBe('+6.8')
    expect(formatDeformationRate(null)).toBe('—')
  })

  it('extracts curve series by component mode correctly', () => {
    const mockData = {
      displacements_mm: [-10, -20],
      trend_displacements_mm: [-8, -18],
      seasonal_elastic_mm: [-2, -2],
      epoch_velocities_mm_yr: [-16.0, -20.0]
    }
    expect(extractCurveSeries(mockData, 'total')).toEqual([-10, -20])
    expect(extractCurveSeries(mockData, 'trend')).toEqual([-8, -18])
    expect(extractCurveSeries(mockData, 'seasonal')).toEqual([-2, -2])
    expect(extractCurveSeries(mockData, 'rate')).toEqual([-16.0, -20.0])
  })

  it('computes cumulative threshold line and dynamic rate slope envelope correctly', () => {
    const res = projectTimeseriesPoints(sampleDisps, sampleEpochs, {
      cumulativeThresholdVal: -30.0,
      rateEnvelopeSlope: -20.0
    })
    expect(res.cumulativeLineY).not.toBeNull()
    expect(res.rateSlopeLine).not.toBeNull()
    expect(res.rateSlopeLine.x1).toBe(35)
    expect(res.rateSlopeLine.y2).toBeGreaterThan(res.rateSlopeLine.y1) // downward slope
  })
})

describe('InsarTimeseriesChart.vue Template & Style Guards', () => {
  it('contains SVG elements, dual risk thresholds, rate slope envelope, and multi-component tabs', () => {
    const s = readChartVue()
    expect(s).toContain('class="insar-ts-card"')
    expect(s).toContain('class="ts-svg"')
    expect(s).toContain('class="rate-slope-line"')
    expect(s).toContain('class="cumu-threshold-line"')
    expect(s).toContain('class="rate-threshold-line"')
    expect(s).toContain('class="curve-stroke"')
    expect(s).toContain('class="ts-curve-tabs"')
    expect(s).toContain('累积总形变')
    expect(s).toContain('塑性趋势项')
    expect(s).toContain('温变弹性项')
    expect(s).toContain('年化沉降速率')
    expect(s).toContain('工程双物理标尺提示')
    expect(s).toContain('lateral-box')
  })
})

describe('CesiumViewer.vue 3D Beacon Guards', () => {
  it('implements setInspectionBeacon and clearInspectionBeacon', () => {
    const s = readCesiumViewerVue()
    expect(s).toContain('function setInspectionBeacon')
    expect(s).toContain('function clearInspectionBeacon')
    expect(s).toContain('setInspectionBeacon,')
    expect(s).toContain('clearInspectionBeacon')
  })
})

describe('App.vue InSAR Timeseries Integration Guards', () => {
  it('imports and registers InsarTimeseriesChart', () => {
    const s = readAppVue()
    expect(s).toContain("import InsarTimeseriesChart from './components/InsarTimeseriesChart.vue'")
    expect(s).toContain('InsarTimeseriesChart')
  })

  it('binds map-click event, timeseries fetcher, and 3D inspection beacon', () => {
    const s = readAppVue()
    expect(s).toContain('@map-click="onMapClick"')
    expect(s).toContain('fetchInsarTimeseries')
    expect(s).toContain('insarTimeseriesData')
    expect(s).toContain('setInspectionBeacon')
    expect(s).toContain('clearInspectionBeacon')
  })
})
