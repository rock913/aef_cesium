<template>
  <div class="heritage-panel" @pointerdown.stop @pointermove.stop @pointerup.stop @wheel.stop>
    <div class="hp-header">
      <div class="hp-title-group">
        <span class="hp-icon">🏯</span>
        <div>
          <div class="hp-name">{{ building?.name || '古建单体' }}</div>
          <div class="hp-id">{{ building?.building_id || '—' }} · {{ building?.protection_level || '—' }} · {{ building?.era || '—' }}</div>
        </div>
      </div>
      <div class="hp-actions">
        <span class="hp-badge" :class="riskClass">{{ fusion?.coupled_risk_level || l3?.risk_level || '—' }}</span>
        <button class="hp-close" type="button" aria-label="关闭" @click="$emit('close')">✕</button>
      </div>
    </div>

    <div class="hp-body">
      <!-- L2 语义 -->
      <div class="hp-meta">
        <span class="hp-meta-k">L2 语义</span>
        <span class="hp-meta-v">{{ l2?.label || '—' }} · conf {{ fmtConfidence(l2?.confidence) }}</span>
      </div>
      <div class="hp-meta">
        <span class="hp-meta-k">L1 卫星</span>
        <span class="hp-meta-v">{{ l1?.source || '—' }} · {{ l1?.resolution_m }}m{{ l1?.data_track === '待接入' ? '（待接入）' : '' }}</span>
      </div>

      <!-- L3 形变五指标 -->
      <div v-if="l3" class="hp-section">
        <div class="hp-section-title">L3 · InSAR 形变五指标 <span class="hp-tag">LOS 相对形变</span></div>
        <div class="hp-grid">
          <div class="hp-cell"><span class="k">最大沉降速率</span><span class="v danger">{{ fmtNum(l3.v_max_mm_yr) }} mm/yr</span></div>
          <div class="hp-cell"><span class="k">沉降速率差</span><span class="v">{{ fmtNum(l3.v_diff_mm_yr) }} mm/yr</span></div>
          <div class="hp-cell"><span class="k">角变形</span><span class="v" :class="{ danger: l3.risk_level === 'unstable' }">{{ l3.beta_ratio || '—' }}</span></div>
          <div class="hp-cell"><span class="k">相干性 γ</span><span class="v">{{ fmtNum(l3.coherence_mean) }}</span></div>
          <div class="hp-cell"><span class="k">时序模式</span><span class="v">{{ l3.temporal_cluster || '—' }}</span></div>
          <div class="hp-cell"><span class="k">风险分级</span><span class="v" :class="riskClass">{{ riskLabel(l3.risk_level) }}</span></div>
        </div>
      </div>

      <!-- L4 病害 -->
      <div v-if="l4" class="hp-section">
        <div class="hp-section-title">L4 · 病害视觉语义 <span class="hp-tag">{{ l4.model?.name || '' }}</span></div>
        <div class="hp-defect">
          <svg class="hp-defect-svg" viewBox="0 0 3456 2304" preserveAspectRatio="xMidYMid meet">
            <image :href="assetUrl(l4.image)" x="0" y="0" width="3456" height="2304" />
            <polygon
              v-for="(poly, i) in defectPolygons"
              :key="i"
              :points="polyPoints(poly)"
              fill="rgba(255,60,60,0.22)"
              stroke="#ff5a5a"
              stroke-width="6"
            />
          </svg>
          <div class="hp-defect-info">
            <div class="hp-defect-type">{{ defectType }}</div>
            <div class="hp-defect-rule">{{ defectRule }}</div>
          </div>
        </div>
      </div>
      <div v-else class="hp-empty">L4 病害台账：候选线索，待实地核实后建立</div>

      <!-- L5 结构风载 -->
      <div v-if="l5" class="hp-section">
        <div class="hp-section-title">L5 · 风载荷薄弱点 <span class="hp-tag">预计算知识库</span></div>
        <div class="hp-weak">
          <img class="hp-fea" :src="assetUrl(l5.fea_weakpoints || l5.fea_panorama)" alt="风载荷云图" />
          <ul class="hp-weak-list">
            <li v-for="w in (l5.weak_points || [])" :key="w.part">
              <span class="hp-weak-rank">{{ w.rank }}</span>
              <span class="hp-weak-part">{{ w.part }}</span>
              <span class="hp-weak-level" :class="'lvl-' + w.level">{{ w.level }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Fusion 耦合研判 -->
      <div v-if="fusion" class="hp-section">
        <div class="hp-section-title">耦合研判 · 证据链</div>
        <ul class="hp-evidence">
          <li v-for="(e, i) in (fusion.evidence_chain || [])" :key="i">{{ e }}</li>
        </ul>
        <div class="hp-reco">{{ fusion.recommendation || '—' }}</div>
      </div>
    </div>

    <div class="hp-footer">
      <span class="hp-tag">演示沙箱轨 · 数据来源角标见各层</span>
      <span class="hp-disclaimer">{{ building?.disclaimer || 'LOS 向相对形变；输出为相对风险排序，非结构安全鉴定结论。' }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  building: { type: Object, default: null }
})
defineEmits(['close'])

const layers = computed(() => props.building?.layers || {})
const l1 = computed(() => layers.value.L1_satellite)
const l2 = computed(() => layers.value.L2_semantic)
const l3 = computed(() => layers.value.L3_deformation)
const l4 = computed(() => layers.value.L4_defect)
const l5 = computed(() => layers.value.L5_structural)
const fusion = computed(() => props.building?.fusion)

const defectPolygons = computed(() => {
  const d = l4.value?.surveys?.[0]?.defects?.[0]
  return d?.polygons || []
})
const defectType = computed(() => l4.value?.surveys?.[0]?.defects?.[0]?.type || '—')
const defectRule = computed(() => l4.value?.surveys?.[0]?.defects?.[0]?.rule || '')

const riskClass = computed(() => {
  const level = fusion.value?.coupled_risk_level || l3.value?.risk_level || ''
  if (typeof level === 'string' && (level.includes('Ⅲ') || level.includes('unstable') || level.includes('优先'))) return 'risk-high'
  if (typeof level === 'string' && (level.includes('Ⅱ') || level.includes('moderate') || level.includes('核查') || level.includes('重点'))) return 'risk-mid'
  return 'risk-low'
})

function assetUrl(name) {
  if (!name) return ''
  return `/api/heritage/assets/${encodeURIComponent(name)}`
}
function fmtNum(x) {
  if (x === null || x === undefined) return '—'
  const n = Number(x)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}
function fmtConfidence(x) {
  if (x === null || x === undefined) return '—'
  const n = Number(x)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}
function riskLabel(level) {
  const map = {
    unstable: '优先核查',
    moderate: '中等关注',
    stable: '基本稳定',
    data_insufficient: '数据不足'
  }
  return map[level] || level || '—'
}
function polyPoints(poly) {
  if (!Array.isArray(poly)) return ''
  return poly.map((p) => `${p[0]},${p[1]}`).join(' ')
}
</script>

<style scoped>
.heritage-panel {
  position: fixed;
  top: 76px;
  right: 16px;
  width: 360px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  background: rgba(8, 14, 22, 0.92);
  border: 1px solid rgba(0, 245, 255, 0.22);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
  color: #d6e4f0;
  font-family: 'ui-monospace', 'SFMono-Regular', 'Menlo', monospace;
  z-index: 60;
  backdrop-filter: blur(8px);
}
.hp-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(0, 245, 255, 0.14);
}
.hp-title-group { display: flex; gap: 10px; }
.hp-icon { font-size: 22px; line-height: 1; }
.hp-name { font-size: 15px; font-weight: 700; color: #fff; }
.hp-id { font-size: 11px; color: #7f9ab0; margin-top: 3px; }
.hp-actions { display: flex; align-items: center; gap: 8px; }
.hp-badge {
  padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 700;
  border: 1px solid rgba(255,255,255,0.16);
}
.risk-high { color: #ff5a5a; border-color: rgba(255,90,90,0.5); }
.risk-mid { color: #ffb84d; border-color: rgba(255,184,77,0.5); }
.risk-low { color: #43d9a3; border-color: rgba(67,217,163,0.5); }
.hp-close {
  background: transparent; border: none; color: #7f9ab0; font-size: 15px; cursor: pointer;
}
.hp-close:hover { color: #fff; }
.hp-body { padding: 12px 14px; display: flex; flex-direction: column; gap: 12px; }
.hp-meta { display: flex; gap: 8px; font-size: 12px; }
.hp-meta-k { color: #5fb3cc; flex-shrink: 0; }
.hp-meta-v { color: #c3d5e4; }
.hp-section { border-top: 1px dashed rgba(0,245,255,0.12); padding-top: 10px; }
.hp-section-title {
  font-size: 12px; font-weight: 700; color: #e8f4ff; margin-bottom: 8px;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.hp-tag {
  font-size: 10px; font-weight: 500; color: #5fb3cc;
  background: rgba(0,245,255,0.08); border: 1px solid rgba(0,245,255,0.18);
  padding: 1px 6px; border-radius: 4px;
}
.hp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; }
.hp-cell { display: flex; justify-content: space-between; font-size: 12px; }
.hp-cell .k { color: #7f9ab0; }
.hp-cell .v { color: #e8f4ff; font-weight: 600; }
.hp-cell .v.danger { color: #ff5a5a; }
.hp-defect { display: flex; flex-direction: column; gap: 8px; }
.hp-defect-svg { width: 100%; border-radius: 6px; background: #000; }
.hp-defect-info { font-size: 11px; }
.hp-defect-type { color: #ffb84d; font-weight: 700; margin-bottom: 3px; }
.hp-defect-rule { color: #8aa4b8; line-height: 1.4; }
.hp-empty { font-size: 11px; color: #8aa4b8; }
.hp-weak { display: flex; gap: 10px; }
.hp-fea { width: 150px; border-radius: 6px; flex-shrink: 0; border: 1px solid rgba(0,245,255,0.2); }
.hp-weak-list { list-style: none; margin: 0; padding: 0; flex: 1; font-size: 11px; }
.hp-weak-list li { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
.hp-weak-rank {
  width: 16px; height: 16px; border-radius: 50%; background: rgba(0,245,255,0.12);
  color: #5fb3cc; font-size: 10px; display: inline-flex; align-items: center; justify-content: center;
}
.hp-weak-part { color: #c3d5e4; flex: 1; }
.hp-weak-level { font-weight: 700; }
.lvl-severe { color: #ff5a5a; }
.lvl-moderate { color: #ffb84d; }
.lvl-minor { color: #43d9a3; }
.hp-evidence { list-style: none; margin: 0 0 8px; padding: 0; font-size: 11px; }
.hp-evidence li { padding-left: 12px; position: relative; margin-bottom: 4px; color: #c3d5e4; }
.hp-evidence li::before { content: '▸'; position: absolute; left: 0; color: #5fb3cc; }
.hp-reco {
  font-size: 12px; color: #43d9a3; background: rgba(67,217,163,0.08);
  border: 1px solid rgba(67,217,163,0.22); border-radius: 6px; padding: 7px 9px;
}
.hp-footer {
  padding: 9px 14px; border-top: 1px solid rgba(0,245,255,0.14);
  display: flex; flex-direction: column; gap: 4px;
}
.hp-disclaimer { font-size: 10px; color: #6f8698; line-height: 1.4; }
</style>
