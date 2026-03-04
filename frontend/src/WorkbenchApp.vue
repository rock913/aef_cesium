<template>
  <div class="workbench-root" data-testid="workbench" aria-label="Zero2x Workbench v7.x">
    <!-- Bottom: engine layer (Z=0) -->
    <EngineScaleRouter
      v-show="activeTab?.kind === 'twin'"
      ref="engineRouter"
      class="engine-layer"
      :scenario="scenario"
      :layers="layers"
      @viewer-ready="onViewerReady"
    />

    <!-- Top: HUD overlay (Z=10). Default pointer-events off; panels opt-in. -->
    <div class="hud-layer pointer-events-none" aria-label="HUD Layer">
      <header class="top-nav glass-panel pointer-events-auto" aria-label="Top Navigation">
        <div class="top-left">
          <div class="brand">ZERO2X 021 WORKBENCH</div>
          <button class="link" type="button" :aria-pressed="mode === 'theater'" @click="setMode('theater')">
            Theater (F11)
          </button>
          <button class="link" type="button" :aria-pressed="mode === 'lab'" @click="setMode('lab')">Lab</button>
        </div>

        <div class="top-center" aria-label="Tabs" v-show="!isImmersive">
          <TabBar
            :tabs="openTabs"
            :active-id="activeTabId"
            @select="setActiveTab"
            @close="closeTab"
            @new-tab="openNewTab"
          />
        </div>

        <div class="top-right" aria-label="Top Actions">
          <div class="scale-toggle" role="group" aria-label="Scale Toggle">
            <button
              class="scale-btn"
              type="button"
              :aria-pressed="researchStore.currentScale === 'earth'"
              :class="{ active: researchStore.currentScale === 'earth' }"
              @click="setScale('earth')"
            >
              Earth
            </button>
            <button
              class="scale-btn"
              type="button"
              :aria-pressed="researchStore.currentScale === 'macro'"
              :class="{ active: researchStore.currentScale === 'macro' }"
              @click="setScale('macro')"
            >
              Macro
            </button>
            <button
              class="scale-btn"
              type="button"
              :aria-pressed="researchStore.currentScale === 'micro'"
              :class="{ active: researchStore.currentScale === 'micro' }"
              @click="setScale('micro')"
            >
              Micro
            </button>
          </div>

          <button class="link" type="button" @click="openOmni">Omni (Cmd/Ctrl+K)</button>
        </div>
      </header>

      <div class="middle-workspace" aria-label="Main Workspace">
        <aside class="left-armor glass-panel pointer-events-auto" aria-label="Agent Flow" v-show="!isImmersive">
          <AgentPanel :text="agentText" @execute="runExecute" @reset="reset" />
        </aside>

        <div class="center-stage" aria-label="Center Stage">
          <div v-if="activeTab?.kind === 'table'" class="center-panel glass-panel pointer-events-auto" aria-label="Data Table">
            <DataTableTab :rows="tableRows" />
          </div>
          <div v-else-if="activeTab?.kind === 'charts'" class="center-panel glass-panel pointer-events-auto" aria-label="Charts">
            <ChartsTab :series="chartSeries" />
          </div>

          <div v-if="activeTab?.kind === 'twin' && !viewerReady" class="engine-status glass-panel pointer-events-auto">
            正在唤醒 Cesium…
          </div>
        </div>

        <aside class="right-armor pointer-events-auto" aria-label="Right Armor" v-show="!isImmersive">
          <div class="glass-panel right-pane right-pane-layers" aria-label="Layer Tree">
            <LayerTree v-model:layers="layers" :current-scale="researchStore.currentScale" />
          </div>

          <div class="glass-panel right-pane right-pane-editor" aria-label="Notebook / Code">
            <EditorPanel>
              <MonacoLazyEditor v-model="code" language="python" />
            </EditorPanel>
          </div>
        </aside>
      </div>

      <div class="bottom-console" aria-label="Bottom Console">
        <div class="glass-panel pointer-events-auto bottom-panel">
          <TimelineHUD @execute="runExecute" />
        </div>
      </div>

      <TheaterHUD
        v-if="isImmersive"
        class="pointer-events-auto"
        :context-id="scenario?.id || ''"
        :target-name="scenario?.targetName || ''"
        :summary="theaterSummary"
        @open-omni="openOmni"
        @switch-lab="setMode('lab')"
      />
    </div>

    <div v-if="isOmniOpen" class="omnibox-layer" aria-label="OmniCommand Layer" @pointerdown.self="closeOmni">
      <OmniCommand
        :open="isOmniOpen"
        v-model="omniText"
        :context-label="scenario?.id || ''"
        :presets="demoPresets"
        @submit="submitOmni"
        @select-preset="applyPreset"
        @close="closeOmni"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MonacoLazyEditor from './components/MonacoLazyEditor.vue'
import { getDefaultScenario021, getScenario021ById, parseWorkbenchContextFromSearch } from './utils/scenarios021.js'
import { apiService } from './services/api.js'
import EngineScaleRouter from './views/workbench/EngineScaleRouter.vue'
import { useResearchStore } from './stores/researchStore.js'
import { TaskQueue } from './utils/taskQueue.js'
import AgentPanel from './views/workbench/components/AgentPanel.vue'
import EditorPanel from './views/workbench/components/EditorPanel.vue'
import TimelineHUD from './views/workbench/components/TimelineHUD.vue'
import OmniCommand from './views/workbench/components/OmniCommand.vue'
import TabBar from './views/workbench/components/TabBar.vue'
import TheaterHUD from './views/workbench/components/TheaterHUD.vue'
import LayerTree from './views/workbench/components/LayerTree.vue'
import DataTableTab from './views/workbench/components/DataTableTab.vue'
import ChartsTab from './views/workbench/components/ChartsTab.vue'

const engineRouter = ref(null)
const viewerReady = ref(false)

const researchStore = useResearchStore()
const executeQueue = new TaskQueue()

const mode = ref('lab')
const isImmersive = computed(() => mode.value === 'theater')

const isOmniOpen = ref(false)
const omniText = ref('')

const contextId = ref('poyang')
const scenario = computed(() => getScenario021ById(contextId.value) || getDefaultScenario021())

const demoPresets = Object.freeze([
  {
    id: 'demo:poyang:theater',
    label: '[展演] 鄱阳湖近十年水网演变',
    contextId: 'poyang',
    scale: 'earth',
    mode: 'theater',
    activeTabKind: 'twin',
    hint: '自动进入沉浸态',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.78 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
    ],
  },
  {
    id: 'demo:yuhang:lab',
    label: '[下钻] 调出余杭城建异动审计算法',
    contextId: 'yuhang',
    scale: 'earth',
    mode: 'lab',
    activeTabKind: 'twin',
    hint: '自动展开代码视图',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.75 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: true, params: { opacity: 0.50, threshold: 0.12, palette: 'FF4D6D' } },
    ],
  },
  {
    id: 'demo:gaia_cluster:macro',
    label: '[v7] Gaia Cluster (Macro EXECUTE)',
    contextId: 'poyang',
    scale: 'macro',
    mode: 'theater',
    activeTabKind: 'twin',
    hint: '宏观：Bloom + Spiral + 高亮/环绕',
    layers: [
      { id: 'bloom', enabled: true, params: { strength: 1.35, threshold: 0.62, radius: 0.18 } },
      { id: 'macro-spiral', enabled: true, params: {} },
    ],
  },
  {
    id: 'demo:protein_fold:micro',
    label: '[v7] Protein Fold (Micro EXECUTE)',
    contextId: 'poyang',
    scale: 'micro',
    mode: 'theater',
    activeTabKind: 'twin',
    hint: '微观：材质调参 + 晶格重组',
    layers: [
      { id: 'bloom', enabled: true, params: { strength: 1.15, threshold: 0.70, radius: 0.12 } },
      { id: 'micro-atoms', enabled: true, params: { opacity: 0.82, transmission: 0.88, ior: 1.45 } },
    ],
  },
  {
    id: 'demo:macro:theater',
    label: '[看宏观] 进入沉浸演示态 (Twin)',
    contextId: 'poyang',
    scale: 'macro',
    mode: 'theater',
    activeTabKind: 'twin',
    hint: '看宏观 => 自动进入沉浸态',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.78 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
    ],
  },
  {
    id: 'demo:micro:lab',
    label: '[看微观] 进入微观演示态 (Twin)',
    contextId: 'poyang',
    scale: 'micro',
    mode: 'lab',
    activeTabKind: 'twin',
    hint: '看微观 => 切换到 Three.js 微观底座',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.78 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
    ],
  },
  {
    id: 'demo:code:lab',
    label: '[看代码] 进入硬核作业态 (Editor)',
    contextId: 'yuhang',
    scale: 'earth',
    mode: 'lab',
    activeTabKind: 'twin',
    hint: '看代码 => 自动进入作业态',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.75 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: true, params: { opacity: 0.50, threshold: 0.12, palette: 'FF4D6D' } },
    ],
  },
  {
    id: 'demo:data:lab',
    label: '[看数据] 打开 Data Table',
    contextId: 'poyang',
    scale: 'earth',
    mode: 'lab',
    activeTabKind: 'table',
    hint: '自动切到表格 Tab',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.78 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
    ],
  },
  {
    id: 'demo:charts:lab',
    label: '[看图表] 打开 2D Charts',
    contextId: 'poyang',
    scale: 'earth',
    mode: 'lab',
    activeTabKind: 'charts',
    hint: '自动切到图表 Tab',
    layers: [
      { id: 'gee-heatmap', enabled: true, params: { opacity: 0.78 } },
      { id: 'boundaries', enabled: false, params: { opacity: 0.90 } },
      { id: 'anomaly-mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
    ],
  },
])

const openTabs = ref([
  { id: 'twin', title: 'Twin View', kind: 'twin', closable: false },
  { id: 'table-1', title: 'Data Table', kind: 'table', closable: true },
  { id: 'charts-1', title: '2D Charts', kind: 'charts', closable: true },
])

const activeTabId = ref('twin')

const activeTab = computed(() => {
  const arr = openTabs.value || []
  return arr.find((t) => t.id === activeTabId.value) || arr[0] || { id: 'twin', title: 'Twin View', kind: 'twin' }
})

function _nextId(prefix) {
  const ids = new Set((openTabs.value || []).map((t) => t.id))
  for (let i = 1; i < 99; i += 1) {
    const id = `${prefix}-${i}`
    if (!ids.has(id)) return id
  }
  return `${prefix}-${Date.now()}`
}

function setActiveTab(id) {
  const v = String(id || '').trim()
  if (!v) return
  const exists = (openTabs.value || []).some((t) => t.id === v)
  if (!exists) return
  activeTabId.value = v
  try {
    window.sessionStorage?.setItem?.('z2x:lastTab', activeTabId.value)
  } catch (_) { }
}

function openNewTab(kind) {
  const k = String(kind || '').trim().toLowerCase()
  if (k !== 'table' && k !== 'charts') return
  const id = _nextId(k)
  const title = k === 'charts' ? '2D Charts' : 'Data Table'
  openTabs.value = [...(openTabs.value || []), { id, title, kind: k, closable: true }]
  setActiveTab(id)
}

function closeTab(id) {
  const v = String(id || '').trim()
  if (!v || v === 'twin') return
  const arr = openTabs.value || []
  const idx = arr.findIndex((t) => t.id === v)
  if (idx < 0) return
  const next = arr.filter((t) => t.id !== v)
  openTabs.value = next
  if (activeTabId.value === v) {
    const fallback = next[idx - 1] || next[idx] || next[0] || { id: 'twin' }
    setActiveTab(fallback.id)
  }
}

function ensureTabKind(kind) {
  const k = String(kind || '').trim().toLowerCase()
  if (k === 'twin') {
    setActiveTab('twin')
    return
  }
  const existing = (openTabs.value || []).find((t) => t.kind === k)
  if (existing) {
    setActiveTab(existing.id)
    return
  }
  openNewTab(k)
}

const layers = ref([
  { id: 'gee-heatmap', name: 'GEE Heatmap', enabled: true, params: { opacity: 0.78 } },
  { id: 'boundaries', name: 'Vector Boundaries', enabled: false, params: { opacity: 0.90 } },
  { id: 'anomaly-mask', name: 'Anomaly Mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
  { id: 'bloom', name: 'Bloom FX', enabled: true, params: { strength: 1.1, threshold: 0.65, radius: 0.15 } },
  { id: 'macro-spiral', name: 'Spiral Arms', enabled: true, params: {} },
  { id: 'micro-atoms', name: 'Atom Lattice', enabled: true, params: { opacity: 0.85, transmission: 0.85, ior: 1.4 } },
])

function _safeJsonParse(s, fallback) {
  try {
    return JSON.parse(String(s || ''))
  } catch (_) {
    return fallback
  }
}

function _normalizeTabs(arr) {
  const a = Array.isArray(arr) ? arr : []
  const out = []
  const seen = new Set()
  for (const t of a) {
    const id = String(t?.id || '').trim()
    const kind = String(t?.kind || '').trim().toLowerCase()
    if (!id || seen.has(id)) continue
    if (kind !== 'twin' && kind !== 'table' && kind !== 'charts') continue
    const title = String(t?.title || (kind === 'twin' ? 'Twin View' : kind === 'table' ? 'Data Table' : '2D Charts')).trim()
    const closable = kind === 'twin' ? false : !!t?.closable
    seen.add(id)
    out.push({ id, kind, title, closable })
  }
  if (!out.some((t) => t.kind === 'twin')) {
    out.unshift({ id: 'twin', title: 'Twin View', kind: 'twin', closable: false })
  }
  return out
}

function _normalizeLayers(arr) {
  const a = Array.isArray(arr) ? arr : []
  const allowed = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask', 'bloom', 'macro-spiral', 'micro-atoms'])
  const defaults = new Map([
    ['gee-heatmap', { id: 'gee-heatmap', name: 'GEE Heatmap', enabled: true, params: { opacity: 0.78 } }],
    ['boundaries', { id: 'boundaries', name: 'Vector Boundaries', enabled: false, params: { opacity: 0.90 } }],
    ['anomaly-mask', { id: 'anomaly-mask', name: 'Anomaly Mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } }],
    ['bloom', { id: 'bloom', name: 'Bloom FX', enabled: true, params: { strength: 1.1, threshold: 0.65, radius: 0.15 } }],
    ['macro-spiral', { id: 'macro-spiral', name: 'Spiral Arms', enabled: true, params: {} }],
    ['micro-atoms', { id: 'micro-atoms', name: 'Atom Lattice', enabled: true, params: { opacity: 0.85, transmission: 0.85, ior: 1.4 } }],
  ])

  const out = []
  const seen = new Set()
  for (const l of a) {
    const id = String(l?.id || '').trim()
    if (!allowed.has(id) || seen.has(id)) continue
    const base = defaults.get(id)
    const p = (l && typeof l === 'object') ? l.params : null
    const baseParams = (base && typeof base === 'object') ? base.params : null
    const opacityRaw = p?.opacity ?? baseParams?.opacity
    const opacity = Number(opacityRaw)
    const nextParams = {
      ...(baseParams || {}),
      ...(p && typeof p === 'object' ? p : {}),
    }
    if (Number.isFinite(opacity)) {
      nextParams.opacity = Math.max(0, Math.min(1, opacity))
    }
    if (id === 'anomaly-mask') {
      const thr = Number(nextParams.threshold)
      if (Number.isFinite(thr)) nextParams.threshold = Math.max(0, Math.min(1, thr))
      if (nextParams.palette !== undefined) nextParams.palette = String(nextParams.palette || '').trim()
    }
    if (id === 'bloom') {
      const s = Number(nextParams.strength)
      if (Number.isFinite(s)) nextParams.strength = Math.max(0, Math.min(3, s))
      const thr = Number(nextParams.threshold)
      if (Number.isFinite(thr)) nextParams.threshold = Math.max(0, Math.min(1, thr))
      const r = Number(nextParams.radius)
      if (Number.isFinite(r)) nextParams.radius = Math.max(0, Math.min(1, r))
    }
    if (id === 'micro-atoms') {
      const tr = Number(nextParams.transmission)
      if (Number.isFinite(tr)) nextParams.transmission = Math.max(0, Math.min(1, tr))
      const ior = Number(nextParams.ior)
      if (Number.isFinite(ior)) nextParams.ior = Math.max(1, Math.min(2, ior))
    }
    out.push({
      id,
      name: String(l?.name || base?.name || id),
      enabled: l?.enabled === undefined ? !!base?.enabled : !!l.enabled,
      params: nextParams,
    })
    seen.add(id)
  }
  for (const [id, base] of defaults.entries()) {
    if (!seen.has(id)) out.push({ ...base })
  }
  return out
}

const tableRows = computed(() => {
  const sc = scenario.value
  return [
    { metric: 'context', value: sc?.id || '—', unit: '' },
    { metric: 'target', value: sc?.targetName || '—', unit: '' },
    { metric: 'mode', value: sc?.backend?.mode || '—', unit: '' },
    { metric: 'location', value: sc?.backend?.location || '—', unit: '' },
  ]
})

const chartSeries = computed(() => {
  const scId = String(scenario.value?.id || '')
  if (scId === 'yuhang') return [6, 11, 9, 14, 22, 20, 27]
  if (scId === 'amazon') return [7, 8, 12, 10, 18, 16, 21]
  return [10, 14, 9, 22, 18, 27, 24]
})

const theaterReport = ref('')
const executeBusy = ref(false)

const theaterSummary = computed(() => {
  const sc = scenario.value
  const q = String(lastIntent.value || '').trim()
  const head = `- Context: ${sc?.id || '—'} (${sc?.targetName || '—'})`
  const intent = q ? `- Intent: ${q}` : `- Intent: ${sc?.label || '—'}`
  const rec = '- Recommendation: 切换 Lab 查看代码与证据链'
  const extra = String(theaterReport.value || '').trim()
  return [
    'Agent (demo):',
    head,
    intent,
    rec,
    extra ? '' : null,
    extra || null,
  ].filter(Boolean).join('\n')
})

function buildCodeStub(s) {
  const id = String(s?.id || '').trim() || 'poyang'
  const fn = id === 'yuhang' ? 'audit_yuhang' : id === 'amazon' ? 'cluster_amazon' : 'analyze_poyang'

  return [
    '# Zero2x Workbench (MVP)',
    '# Goal: keep Landing fast; load Cesium+Monaco only here.',
    `# Context: ${id}`,
    '',
    `def ${fn}():`,
    '    """Demo stub: replace with real backend calls."""',
    `    return {"context": "${id}", "status": "stub"}`,
    '',
    `print(${fn}())`,
  ].join('\n')
}

const code = ref(buildCodeStub(scenario.value))

const agentText = ref('System ready. Press Run to simulate an agent flow…')
const lastIntent = ref('')

let _timer = null

function _stop() {
  if (_timer) {
    clearInterval(_timer)
    _timer = null
  }
}

function _type(text) {
  _stop()
  agentText.value = ''
  let i = 0
  _timer = setInterval(() => {
    i += 1
    agentText.value = text.slice(0, i)
    if (i >= text.length) _stop()
  }, 8)
}

function runStub() {
  const q = String(lastIntent.value || '').trim()
  const sc = scenario.value
  const plan = [
    'Agent (demo):',
    `- Context: ${sc?.id || '—'} (${sc?.targetName || '—'})`,
    q ? `- Intent: ${q}` : `- Intent: ${sc?.label || 'Select a scenario from Landing'}`,
    `- Backend: mode=${sc?.backend?.mode || '—'}, location=${sc?.backend?.location || '—'}`,
    '- Step 1: select datasets + time window',
    '- Step 2: compute anomalies / clustering / audits with evidence',
    '- Step 3: render overlays in Cesium Twin and export a short report',
    '',
    'Tip: use /demo for visual validation; keep /workbench for workflows.',
  ].join('\n')

  _type(plan)
}

async function runExecute() {
  try {
    if (executeBusy.value) return
    executeBusy.value = true
    theaterReport.value = ''

    // Always maximize impact: Twin first.
    ensureTabKind('twin')

    const scale = researchStore.currentScale.value

    await executeQueue.enqueue(async () => {
      const sc = scenario.value
      const q = String(lastIntent.value || '').trim()

      if (scale === 'macro') {
        const intro = [
          'Agent (v7):',
          `- Scale: macro`,
          `- Context: ${sc?.id || '—'} (${sc?.targetName || '—'})`,
          q ? `- Intent: ${q}` : `- Intent: ${sc?.label || '—'}`,
          '- Step 1: 调参 LayerTree -> Bloom/Spiral',
          '- Step 2: 高亮星系簇 + 环绕镜头',
        ].join('\n')
        _type(intro)

        await engineRouter.value?.highlightMacroCluster?.()
        await engineRouter.value?.spinMacroCamera?.({ duration: 3.0, revolutions: 1.0 })
        theaterReport.value = [
          'Macro brief:',
          '- 已在 ThreeTwin 中执行高亮与环绕。',
          '- 可用 LayerTree 调整 Bloom Strength/Threshold/Radius。',
        ].join('\n')
        return
      }

      if (scale === 'micro') {
        const intro = [
          'Agent (v7):',
          `- Scale: micro`,
          `- Context: ${sc?.id || '—'} (${sc?.targetName || '—'})`,
          q ? `- Intent: ${q}` : `- Intent: ${sc?.label || '—'}`,
          '- Step 1: 调参 LayerTree -> Material',
          '- Step 2: 晶格重组动画 (rebuild)',
        ].join('\n')
        _type(intro)

        await engineRouter.value?.rebuildMicroLattice?.()
        theaterReport.value = [
          'Micro brief:',
          '- 已触发晶格扰动与回稳。',
          '- 可用 LayerTree 调整 Opacity/Transmission/IOR。',
        ].join('\n')
        return
      }

      // earth (default)
      const backend = sc?.backend || {}
      const modeId = String(backend.mode || '').trim()
      const locationId = String(backend.location || '').trim()
      const missionId = String(backend.mission_id || '').trim()

      const intro = [
        'Agent (demo):',
        `- Scale: earth`,
        `- Context: ${sc?.id || '—'} (${sc?.targetName || '—'})`,
        q ? `- Intent: ${q}` : `- Intent: ${sc?.label || '—'}`,
        `- Backend: mode=${modeId || '—'}, location=${locationId || '—'}`,
        '- Step 1: 准备图层 (tiles/geojson)',
        '- Step 2: 计算统计 (stats)',
        '- Step 3: 生成研判 (analysis/report)',
      ].join('\n')
      _type(intro)

      // Ensure required layers are enabled for a meaningful render.
      try {
        layers.value = (layers.value || []).map((l) => {
          if (l.id === 'gee-heatmap') return { ...l, enabled: true }
          return l
        })
      } catch (_) {
        // ignore
      }

      // If backend isn't ready, keep the UI responsive and stay deterministic.
      try {
        const health = await apiService.healthCheck()
        if (!health?.gee_initialized) {
          theaterReport.value = [
            'Backend note:',
            '- GEE 未初始化，已保留 UI→引擎联动链路。',
            '- 如需真实 tiles，请配置后端 Earth Engine 环境。'
          ].join('\n')
          return
        }
      } catch (_) {
        // ignore health failures; proceed best-effort
      }

      // Stats + analysis/report are optional but upgrade Theater HUD to “business-grade”.
      if (modeId && locationId) {
        const statsResp = await apiService.getStats(modeId, locationId)
        const stats = statsResp?.stats

        let analysisText = ''
        if (missionId) {
          try {
            const analysisResp = await apiService.getAnalysis(missionId, stats)
            analysisText = String(analysisResp?.analysis || '').trim()
          } catch (_) {
            analysisText = ''
          }
        }

        let reportText = ''
        if (missionId) {
          try {
            const reportResp = await apiService.getReport(missionId, stats)
            reportText = String(reportResp?.report || '').trim()
          } catch (_) {
            reportText = ''
          }
        }

        const lines = []
        if (analysisText) {
          lines.push('Analysis:', analysisText)
        }
        if (reportText) {
          if (lines.length) lines.push('')
          lines.push('Brief:', reportText)
        }
        if (lines.length) theaterReport.value = lines.join('\n')
      }
    })
  } catch (e) {
    theaterReport.value = `Backend error: ${e?.message || String(e)}`
  } finally {
    // In Theater mode we want the HUD narrative to be front-and-center.
    setMode('theater')
    executeBusy.value = false
  }
}

function reset() {
  agentText.value = 'System ready. Press Run to simulate an agent flow…'
}

function _flyToScenario() {
  try {
    engineRouter.value?.flyToScenario?.()
  } catch (_) { }
}

function onViewerReady() {
  viewerReady.value = true
  _flyToScenario()
}

function setMode(next) {
  const v = String(next || '').trim().toLowerCase()
  mode.value = v === 'theater' ? 'theater' : 'lab'
  try {
    window.sessionStorage?.setItem?.('z2x:lastMode', mode.value)
  } catch (_) { }

  // In Theater mode, default back to Twin View to maximize impact.
  if (mode.value === 'theater') ensureTabKind('twin')
}

function setScale(scale) {
  try {
    researchStore.setScale(scale)
    window.sessionStorage?.setItem?.('z2x:lastScale', String(scale || ''))
  } catch (_) {
    // ignore
  }
}

function openOmni() {
  isOmniOpen.value = true
}

function closeOmni() {
  isOmniOpen.value = false
}

function submitOmni() {
  // MVP: treat OmniCommand input as the lastIntent and replay the demo plan.
  try {
    lastIntent.value = String(omniText.value || '').trim()
    window.sessionStorage?.setItem?.('z2x:lastIntent', lastIntent.value)
  } catch (_) { }
  closeOmni()
  runStub()
}

function applyPreset(preset) {
  const p = preset || {}
  const nextContext = String(p.contextId || '').trim().toLowerCase()
  if (nextContext) contextId.value = nextContext
  setMode(p.mode)

  if (p.scale) setScale(p.scale)

  if (p.activeTabKind) ensureTabKind(p.activeTabKind)

  if (Array.isArray(p.layers) && p.layers.length) {
    try {
      layers.value = _normalizeLayers(p.layers)
    } catch (_) {
      // ignore
    }
  }

  try {
    window.sessionStorage?.setItem?.('z2x:lastContext', contextId.value)
  } catch (_) { }

  try {
    const u = new URL(window.location.href)
    u.searchParams.set('context', contextId.value)
    window.history.replaceState({}, '', u.toString())
  } catch (_) {
    // ignore
  }

  closeOmni()
  runStub()
}

function onKeydown(e) {
  if (!e) return
  const k = String(e.key || '').toLowerCase()
  if (k === 'f11') {
    e.preventDefault()
    setMode(isImmersive.value ? 'lab' : 'theater')
    return
  }
  if ((e.metaKey || e.ctrlKey) && k === 'k') {
    e.preventDefault()
    openOmni()
    return
  }
  if (k === 'escape' && isOmniOpen.value) {
    closeOmni()
  }
}

watch(
  () => scenario.value?.id,
  () => {
    code.value = buildCodeStub(scenario.value)
    if (viewerReady.value) _flyToScenario()
  }
)

watch(
  () => openTabs.value,
  (v) => {
    try {
      window.sessionStorage?.setItem?.('z2x:openTabs', JSON.stringify(v))
    } catch (_) { }
  },
  { deep: true }
)

watch(
  () => layers.value,
  (v) => {
    try {
      window.sessionStorage?.setItem?.('z2x:layers', JSON.stringify(v))
    } catch (_) { }
  },
  { deep: true }
)

watch(
  () => researchStore.currentScale.value,
  () => {
    try {
      executeQueue.cancel('scale-switch')
    } catch (_) {
      // ignore
    }
  }
)

onMounted(() => {
  try {
    document.body.style.overflow = 'hidden'
  } catch (_) {
    // ignore
  }

  window.addEventListener('keydown', onKeydown)

  try {
    const ctxFromUrl = parseWorkbenchContextFromSearch(window.location.search)
    const ctxFromStorage = window.sessionStorage?.getItem?.('z2x:lastContext') || ''
    contextId.value = String(ctxFromUrl || ctxFromStorage || 'poyang').trim().toLowerCase() || 'poyang'

    const scaleFromStorage = window.sessionStorage?.getItem?.('z2x:lastScale') || ''
    if (String(scaleFromStorage).trim()) {
      try {
        researchStore.setScale(scaleFromStorage)
      } catch (_) {
        // ignore
      }
    }

    const m = window.sessionStorage?.getItem?.('z2x:lastMode') || ''
    mode.value = String(m).trim().toLowerCase() === 'theater' ? 'theater' : 'lab'

    const tabsRaw = window.sessionStorage?.getItem?.('z2x:openTabs') || ''
    const tabsParsed = _normalizeTabs(_safeJsonParse(tabsRaw, null))
    if (tabsParsed && tabsParsed.length) {
      openTabs.value = tabsParsed
    }

    const lastTab = window.sessionStorage?.getItem?.('z2x:lastTab') || ''
    if (String(lastTab).trim()) setActiveTab(lastTab)

    const layersRaw = window.sessionStorage?.getItem?.('z2x:layers') || ''
    const layersParsed = _normalizeLayers(_safeJsonParse(layersRaw, null))
    if (layersParsed && layersParsed.length) {
      layers.value = layersParsed
    }

    lastIntent.value = window.sessionStorage?.getItem?.('z2x:lastIntent') || ''
    window.sessionStorage?.setItem?.('z2x:lastContext', contextId.value)
  } catch (_) {
    lastIntent.value = ''
  }

  // Golden path: auto-play a short demo when arriving from Act2.
  setTimeout(() => runStub(), 220)
})

onBeforeUnmount(() => {
  _stop()
  try {
    document.body.style.overflow = 'auto'
  } catch (_) {
    // ignore
  }

  try {
    window.removeEventListener('keydown', onKeydown)
  } catch (_) {
    // ignore
  }
})
</script>

<style scoped>

.workbench-root {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #000;
  color: rgba(235, 245, 255, 0.92);
}

.engine-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hud-layer {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 24px;
  background:
    radial-gradient(1200px 900px at 50% 0%, rgba(0, 240, 255, 0.08), rgba(0, 0, 0, 0)),
    radial-gradient(900px 600px at 50% 35%, rgba(120, 160, 255, 0.10), rgba(0, 0, 0, 0.25));
}

.glass-panel {
  background: rgba(10, 15, 26, 0.45);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(0, 240, 255, 0.15);
  border-radius: 12px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.30);
}

.top-nav {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 320px;
}

.brand {
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  letter-spacing: 0.18em;
  color: rgba(0, 240, 255, 0.95);
  font-weight: 900;
  white-space: nowrap;
}

.top-center {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: center;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
  min-width: 320px;
}

.link {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
}

.link:hover {
  color: rgba(255, 255, 255, 0.96);
}

.scale-toggle {
  display: flex;
  gap: 6px;
  padding: 4px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(255, 255, 255, 0.04);
}

.scale-btn {
  border: 1px solid transparent;
  background: transparent;
  color: rgba(255, 255, 255, 0.65);
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 10px;
  cursor: pointer;
}

.scale-btn.active {
  background: rgba(0, 240, 255, 0.16);
  border-color: rgba(0, 240, 255, 0.28);
  color: rgba(0, 240, 255, 0.95);
  text-shadow: 0 0 18px rgba(0, 240, 255, 0.25);
}

.middle-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  margin: 18px 0;
}

.left-armor {
  width: 360px;
  flex-shrink: 0;
  padding: 12px;
  overflow: hidden;
}

.center-stage {
  flex: 1;
  min-width: 0;
  position: relative;
}

.center-panel {
  height: 100%;
  padding: 12px;
  overflow: auto;
}

.engine-status {
  position: absolute;
  left: 0;
  bottom: 0;
  padding: 10px 12px;
  font-size: 12px;
}

.right-armor {
  width: 420px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.right-pane {
  padding: 12px;
  min-height: 0;
  overflow: hidden;
}

.right-pane-layers {
  max-height: 42vh;
  overflow: hidden;
}

.right-pane-editor {
  flex: 1;
  overflow: hidden;
}

.bottom-console {
  height: 72px;
}

.bottom-panel {
  height: 100%;
  padding: 10px 12px;
  overflow: hidden;
}

.omnibox-layer {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: start center;
  padding-top: 64px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(6px);
}

:global(::-webkit-scrollbar) {
  width: 4px;
  height: 4px;
}

:global(::-webkit-scrollbar-thumb) {
  background: rgba(0, 240, 255, 0.2);
  border-radius: 4px;
}

@media (max-width: 980px) {
  .left-armor {
    width: 320px;
  }
  .right-armor {
    width: 360px;
  }
}

@media (max-width: 860px) {
  .middle-workspace {
    flex-direction: column;
  }
  .left-armor,
  .right-armor {
    width: 100%;
  }
  .right-pane-layers {
    max-height: 260px;
  }
}
</style>
