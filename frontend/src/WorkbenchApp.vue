<template>
  <div class="wb" data-testid="workbench">
    <div class="ide" aria-label="Zero2x Spatial IDE">
      <header class="ide-top" aria-label="Workbench Top Bar">
        <div class="ide-title">ZERO2X 021 WORKBENCH</div>
        <div class="ide-top-center" aria-label="Explicit Mode Toggle">
          <div class="mode-toggle" role="group" aria-label="Mode Toggle">
            <button
              class="mode-btn"
              type="button"
              :aria-pressed="mode === 'theater'"
              :class="{ active: mode === 'theater' }"
              @click="setMode('theater')"
            >
              🎬 沉浸汇报视图 (Theater / F11)
            </button>
            <button
              class="mode-btn"
              type="button"
              :aria-pressed="mode === 'lab'"
              :class="{ active: mode === 'lab' }"
              @click="setMode('lab')"
            >
              🛠️ 硬核分析视图 (Lab)
            </button>
            <div class="mode-knob" :class="{ right: mode === 'lab' }" aria-hidden="true"></div>
          </div>
        </div>
        <div class="ide-top-actions" aria-label="Top Actions">
          <button class="top-link" type="button" @click="openOmni">Omni (Cmd/Ctrl+K)</button>
        </div>
      </header>

      <div class="ide-body">
        <aside
          class="ide-aside left"
          :class="{ collapsed: isImmersive }"
          aria-label="Agent Sidebar"
        >
          <AgentPanel :text="agentText" @execute="runExecute" @reset="reset" />
        </aside>

        <main class="ide-main" aria-label="Main Canvas">
          <div v-show="!isImmersive" class="ide-tabs" aria-label="Tabs">
            <TabBar
              :tabs="openTabs"
              :active-id="activeTabId"
              @select="setActiveTab"
              @close="closeTab"
              @new-tab="openNewTab"
            />
          </div>

          <div class="ide-canvas" aria-label="Canvas">
            <EngineRouter
              v-show="activeTab?.kind === 'twin'"
              ref="engineRouter"
              :scenario="scenario"
              :layers="layers"
              @viewer-ready="onViewerReady"
            />
            <div v-if="activeTab?.kind === 'twin' && !viewerReady" class="engine-status">正在唤醒 Cesium…</div>

            <DataTableTab v-if="activeTab?.kind === 'table'" :rows="tableRows" />
            <ChartsTab v-if="activeTab?.kind === 'charts'" :series="chartSeries" />

            <LayerTree v-model:layers="layers" />

            <TheaterHUD
              v-if="isImmersive"
              :context-id="scenario?.id || ''"
              :target-name="scenario?.targetName || ''"
              :summary="theaterSummary"
              @open-omni="openOmni"
              @switch-lab="setMode('lab')"
            />

            <TimelineHUD class="timeline-hud" @execute="runExecute" />
          </div>
        </main>

        <aside
          class="ide-aside right"
          :class="{ collapsed: isImmersive }"
          aria-label="Editor Sidebar"
        >
          <EditorPanel>
            <MonacoLazyEditor v-model="code" language="python" />
          </EditorPanel>
        </aside>
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
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MonacoLazyEditor from './components/MonacoLazyEditor.vue'
import { getDefaultScenario021, getScenario021ById, parseWorkbenchContextFromSearch } from './utils/scenarios021.js'
import { apiService } from './services/api.js'
import EngineRouter from './views/workbench/EngineRouter.vue'
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
    id: 'demo:macro:theater',
    label: '[看宏观] 进入沉浸演示态 (Twin)',
    contextId: 'poyang',
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
    id: 'demo:code:lab',
    label: '[看代码] 进入硬核作业态 (Editor)',
    contextId: 'yuhang',
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
  const allowed = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask'])
  const defaults = new Map([
    ['gee-heatmap', { id: 'gee-heatmap', name: 'GEE Heatmap', enabled: true, params: { opacity: 0.78 } }],
    ['boundaries', { id: 'boundaries', name: 'Vector Boundaries', enabled: false, params: { opacity: 0.90 } }],
    ['anomaly-mask', { id: 'anomaly-mask', name: 'Anomaly Mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } }],
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
  if (executeBusy.value) return
  executeBusy.value = true
  theaterReport.value = ''

  try {
    // Always maximize impact: Twin first.
    ensureTabKind('twin')

    const sc = scenario.value
    const backend = sc?.backend || {}
    const modeId = String(backend.mode || '').trim()
    const locationId = String(backend.location || '').trim()
    const missionId = String(backend.mission_id || '').trim()

    const q = String(lastIntent.value || '').trim()
    const intro = [
      'Agent (demo):',
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
.wb {
  position: relative;
  width: 100vw;
  height: 100vh;
  background: #000;
  color: #eef2ff;
  overflow: hidden;
}

.ide {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: radial-gradient(1200px 800px at 50% 20%, rgba(120, 160, 255, 0.10), rgba(0, 0, 0, 0.25)),
    linear-gradient(180deg, #05070f, #000);
}

.ide-top {
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  padding: 0 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(5, 8, 16, 0.86);
}

.ide-title {
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  letter-spacing: 0.18em;
  color: rgba(0, 240, 255, 0.95);
  font-weight: 900;
}

.ide-top-actions {
  display: flex;
  gap: 10px;
}

.ide-top-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.mode-toggle {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 0;
  padding: 3px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.10), rgba(0, 0, 0, 0.35)),
    radial-gradient(700px 60px at 50% 0%, rgba(0, 240, 255, 0.18), rgba(0, 0, 0, 0));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.10),
    0 10px 30px rgba(0, 0, 0, 0.55);
  min-width: min(560px, calc(100vw - 220px));
  max-width: 720px;
}

.mode-btn {
  position: relative;
  z-index: 2;
  border: none;
  background: transparent;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mode-btn.active {
  color: rgba(0, 0, 0, 0.90);
  font-weight: 900;
}

.mode-knob {
  position: absolute;
  inset: 3px;
  width: calc(50% - 3px);
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(0, 240, 255, 0.62)),
    radial-gradient(60px 22px at 20% 20%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    0 8px 22px rgba(0, 0, 0, 0.45);
  transform: translateX(0);
  transition: transform 320ms cubic-bezier(0.4, 0, 0.2, 1);
}

.mode-knob.right {
  transform: translateX(calc(100% + 3px));
}

.top-link {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  cursor: pointer;
}

.top-link:hover {
  color: rgba(255, 255, 255, 0.95);
}

.ide-body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.ide-aside {
  width: 360px;
  flex-shrink: 0;
  padding: 12px;
  background: rgba(10, 15, 26, 0.92);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
  transition:
    width 420ms cubic-bezier(0.4, 0, 0.2, 1),
    padding 420ms cubic-bezier(0.4, 0, 0.2, 1),
    transform 420ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 420ms cubic-bezier(0.4, 0, 0.2, 1);
}

.ide-aside.right {
  width: 420px;
  border-right: none;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.ide-aside.collapsed {
  width: 0 !important;
  padding: 0;
  opacity: 0;
  border-color: transparent;
}

.ide-aside.left.collapsed {
  transform: translateX(-24px);
}

.ide-aside.right.collapsed {
  transform: translateX(24px);
}

.ide-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #000;
}

.ide-tabs {
  height: 32px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(5, 8, 16, 0.86);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.tab {
  padding: 6px 12px;
  font-size: 12px;
  border-top: 2px solid transparent;
  opacity: 0.72;
}

.tab.active {
  opacity: 0.95;
  border-top-color: rgba(0, 240, 255, 0.95);
  background: rgba(0, 0, 0, 0.55);
}

.tab.ghost {
  opacity: 0.45;
}

.ide-canvas {
  position: relative;
  flex: 1;
  min-height: 0;
}

.engine-status {
  position: absolute;
  left: 18px;
  bottom: 18px;
  z-index: 5;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.10);
  font-size: 12px;
  backdrop-filter: blur(12px);
}

.timeline-hud {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 18px;
  z-index: 6;
  pointer-events: auto;
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

@media (max-width: 980px) {
  .ide-aside {
    width: 320px;
  }
  .ide-aside.right {
    width: 360px;
  }
}

@media (max-width: 860px) {
  .ide-body {
    flex-direction: column;
  }
  .ide-aside,
  .ide-aside.right {
    width: 100%;
    height: 260px;
  }
}
</style>
