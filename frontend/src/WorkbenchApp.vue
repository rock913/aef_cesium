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

    <!-- Swipe split UI: above engine, below all HUD controls -->
    <SwipeHUD
      :active="swipeEnabled && currentScale === 'earth' && activeTab?.kind === 'twin'"
      v-model:position="swipePosition"
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
              :aria-pressed="currentScale === 'earth'"
              :class="{ active: currentScale === 'earth' }"
              @click="setScale('earth')"
            >
              Earth
            </button>
            <button
              class="scale-btn"
              type="button"
              :aria-pressed="currentScale === 'macro'"
              :class="{ active: currentScale === 'macro' }"
              @click="setScale('macro')"
            >
              Sky
            </button>
            <button
              class="scale-btn"
              type="button"
              :aria-pressed="currentScale === 'micro'"
              :class="{ active: currentScale === 'micro' }"
              @click="setScale('micro')"
            >
              Micro
            </button>
          </div>

          <button class="link" type="button" @click="openCommandPalette">Command (Cmd/Ctrl+K)</button>
        </div>
      </header>

      <div class="middle-workspace" aria-label="Main Workspace">
        <aside class="left-rail glass-panel pointer-events-auto" aria-label="Unified Artifacts" v-show="!isImmersive">
          <UnifiedArtifactsPanel
            v-model:layers="layers"
            v-model:code="code"
            v-model:swipe-enabled="swipeEnabled"
            :current-scale="currentScale"
            :report-text="theaterReport"
            :charts="charts"
          />
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

        <aside class="right-rail glass-panel pointer-events-auto" aria-label="021 Copilot Chat" v-show="!isImmersive">
          <CopilotChatPanel
            ref="copilotPanel"
            :busy="executeBusy"
            :presets="copilotPresets"
            :chat-history="chatHistory"
            @select-preset="onCopilotSelectPreset"
            @submit="onCopilotSubmit"
          />
        </aside>
      </div>

      <div
        v-if="showTimelineHud"
        class="timeline-float glass-panel pointer-events-auto"
        aria-label="Contextual Timeline"
      >
        <TimelineHUD
          :min-year="timelineRange.minYear"
          :max-year="timelineRange.maxYear"
          :progress="timelineProgress"
          :is-playing="timelineIsPlaying"
          :is-loading="timelineIsLoading"
          @toggle-play="onTimelineTogglePlay"
          @seek="onTimelineSeek"
        />
      </div>

      <TheaterHUD
        v-if="isImmersive"
        class="pointer-events-auto"
        :context-id="scenario?.id || ''"
        :target-name="scenario?.targetName || ''"
        :summary="theaterSummary"
        @open-omni="openCommandPalette"
        @switch-lab="setMode('lab')"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getDefaultScenario021, getScenario021ById, parseWorkbenchContextFromSearch } from './utils/scenarios021.js'
import { applyCopilotArtifacts } from './utils/copilotArtifacts.js'
import { apiService } from './services/api.js'
import EngineScaleRouter from './views/workbench/EngineScaleRouter.vue'
import { useResearchStore } from './stores/researchStore.js'
import { TaskQueue } from './utils/taskQueue.js'
import TimelineHUD from './views/workbench/components/TimelineHUD.vue'
import SwipeHUD from './views/workbench/components/SwipeHUD.vue'
import TabBar from './views/workbench/components/TabBar.vue'
import TheaterHUD from './views/workbench/components/TheaterHUD.vue'
import DataTableTab from './views/workbench/components/DataTableTab.vue'
import ChartsTab from './views/workbench/components/ChartsTab.vue'
import UnifiedArtifactsPanel from './views/workbench/components/UnifiedArtifactsPanel.vue'
import CopilotChatPanel from './views/workbench/components/CopilotChatPanel.vue'

const engineRouter = ref(null)
const copilotPanel = ref(null)
const viewerReady = ref(false)

const researchStore = useResearchStore()
const currentScale = researchStore.currentScale
const executeQueue = new TaskQueue()

const mode = ref('lab')
const isImmersive = computed(() => mode.value === 'theater')

const swipeEnabled = ref(false)
const swipePosition = ref(0.5)

const timelineProgress = ref(30)
const timelineIsPlaying = ref(false)
const timelineIsLoading = ref(false)
let _timelineTimer = null

function _stopTimeline() {
  timelineIsPlaying.value = false
  timelineIsLoading.value = false
  if (_timelineTimer) {
    clearInterval(_timelineTimer)
    _timelineTimer = null
  }
}

function onTimelineSeek(v) {
  const n = Number(v)
  timelineProgress.value = Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : 0
}

function onTimelineTogglePlay() {
  // Controlled component: parent decides how to advance.
  // If no real timeseries driver is wired, we keep this as a no-op unless
  // explicitly forced on (URL/env) for demo purposes.
  if (timelineIsPlaying.value) {
    _stopTimeline()
    return
  }

  timelineIsPlaying.value = true

  if (!_forceTimelineUi) {
    // No driver: immediately fall back to paused state.
    timelineIsPlaying.value = false
    return
  }

  _timelineTimer = setInterval(() => {
    timelineProgress.value = (timelineProgress.value + 1) % 101
  }, 240)
}


const contextId = ref('poyang')
const scenario = computed(() => getScenario021ById(contextId.value) || getDefaultScenario021())

const currentContextHasTime = computed(() => {
  const s = scenario.value
  if (s?.hasTime) return true
  try {
    const ids = new Set((layers.value || []).filter((l) => !!l?.enabled).map((l) => String(l?.id || '')))
    if (ids.has('gee-heatmap') || ids.has('anomaly-mask')) return true
  } catch (_) {
    // ignore
  }
  return false
})

const _forceTimelineUi = (() => {
  try {
    const u = new URL(String(window?.location?.href || ''))
    const v = String(u.searchParams.get('timeline') || '').trim().toLowerCase()
    if (v === '1' || v === 'true') return true
  } catch (_) {
    // ignore
  }
  try {
    return String(import.meta.env?.VITE_ENABLE_TIMELINE_UI || '').trim() === '1'
  } catch (_) {
    return false
  }
})()

const isTimeSeriesDataReady = computed(() => {
  // Patch 0303: hide timeline unless we are confident a real timeseries driver
  // is wired (or explicitly forced on for demos).
  if (_forceTimelineUi) return true
  return false
})

const showTimelineHud = computed(() => {
  if (activeTab.value?.kind !== 'twin') return false
  if (!currentContextHasTime.value) return false
  if (!isTimeSeriesDataReady.value) return false
  return true
})

const timelineRange = computed(() => {
  const s = scenario.value
  const minYear = Number(s?.timeRange?.minYear)
  const maxYear = Number(s?.timeRange?.maxYear)
  return {
    minYear: Number.isFinite(minYear) ? minYear : 2017,
    maxYear: Number.isFinite(maxYear) ? maxYear : 2024,
  }
})

function _applySwipeToEngine() {
  try {
    engineRouter.value?.setSwipeMode?.({
      enabled: !!swipeEnabled.value,
      position: swipePosition.value,
    })
  } catch (_) {
    // ignore
  }
}

// Patch 0303: Swipe toggle UI lives in the Layers panel (not the top nav).
// swipeEnabled changes are handled via a watcher.

const _initialSearch = (() => {
  try {
    return String(window?.location?.search || '')
  } catch (_) {
    return ''
  }
})()

const _contextFromUrl = (() => {
  try {
    return String(parseWorkbenchContextFromSearch(_initialSearch) || '').trim().toLowerCase()
  } catch (_) {
    return ''
  }
})()

const _scaleFromUrl = (() => {
  try {
    const u = new URL(String(window?.location?.href || ''))
    return String(u.searchParams.get('scale') || '').trim().toLowerCase()
  } catch (_) {
    return ''
  }
})()

const _autoplayFromUrl = (() => {
  try {
    const qs = typeof _initialSearch === 'string' ? _initialSearch : ''
    const sp = new URLSearchParams(qs.startsWith('?') ? qs : `?${qs}`)
    const autoplay = String(sp.get('autoplay') || '').trim().toLowerCase()
    const from = String(sp.get('from') || '').trim().toLowerCase()
    return autoplay === '1' || autoplay === 'true' || from === 'act2'
  } catch (_) {
    return false
  }
})()

// Initialize context/scale early to avoid mount-then-unmount races (Cesium init) on first paint.
try {
  const ctxFromStorage = String(window?.sessionStorage?.getItem?.('z2x:lastContext') || '').trim().toLowerCase()
  contextId.value = _contextFromUrl || ctxFromStorage || 'poyang'
} catch (_) {
  contextId.value = _contextFromUrl || 'poyang'
}

try {
  const scaleFromStorage = String(window?.sessionStorage?.getItem?.('z2x:lastScale') || '').trim().toLowerCase()
  const initialScale = _scaleFromUrl || (_contextFromUrl ? 'earth' : scaleFromStorage)
  if (initialScale) researchStore.setScale(initialScale)
} catch (_) {
  // ignore
}

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
    label: '[v7] Gaia Cluster (Sky EXECUTE)',
    contextId: 'poyang',
    scale: 'macro',
    mode: 'theater',
    activeTabKind: 'twin',
    hint: 'Sky：Bloom + Spiral + 高亮/环绕',
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
    label: '[看 Sky] 进入沉浸演示态 (Twin)',
    contextId: 'poyang',
    scale: 'macro',
    mode: 'theater',
    activeTabKind: 'twin',
    hint: 'Sky => 自动进入沉浸态',
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

const copilotPresets = ref([
  {
    id: 'demo:yuhang_audit',
    label: '[演示] 余杭城建审计',
    prompt: '对比余杭近7年的城建扩张，使用欧氏距离算子，生成城建审计图层。'
  },
  {
    id: 'demo:amazon_cluster',
    label: '[演示] 亚马逊零样本聚类',
    prompt: '扫描当前视窗，不使用先验标签，根据 AlphaEarth 64维特征进行零样本聚类(k=6)，找出毁林区。'
  },
  {
    id: 'demo:maowusu_cos',
    label: '[演示] 毛乌素生态穿透',
    prompt: '评估毛乌素沙地近5年真实治理成效，改用余弦相似度以排除秋冬植被枯黄干扰。'
  },
  {
    id: 'demo:wormhole_micro',
    label: '[演示] 宏微虫洞跃迁',
    prompt: '触发虫洞动画并切换到 micro，生成 SiO2 分子晶格。'
  },
])

const copilotEvents = ref([])

const chatHistory = ref([
  {
    id: 'init',
    role: 'assistant',
    content: 'System ready. 欢迎使用 021 Copilot。请选择预置剧本或直接输入指令。',
    events: [],
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
  { id: 'gee-heatmap', name: 'GEE Heatmap', enabled: false, params: { opacity: 0.78 } },
  { id: 'boundaries', name: 'Vector Boundaries', enabled: false, params: { opacity: 0.90 } },
  { id: 'anomaly-mask', name: 'Anomaly Mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } },
  { id: 'ai-imagery', name: 'AI Imagery Overlay', enabled: false, params: { opacity: 0.65, tile_url: '' } },
  { id: 'ai-vector', name: 'AI Vector Overlay', enabled: false, params: { opacity: 0.90, geojson: null } },
  { id: 'bloom', name: 'Bloom FX', enabled: true, params: { strength: 1.1, threshold: 0.65, radius: 0.15 } },
  { id: 'macro-spiral', name: 'Spiral Arms', enabled: true, params: {} },
  { id: 'micro-atoms', name: 'Atom Lattice', enabled: true, params: { opacity: 0.85, transmission: 0.85, ior: 1.4 } },
])

const charts = ref([])

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
  const allowed = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask', 'ai-imagery', 'ai-vector', 'bloom', 'macro-spiral', 'micro-atoms'])
  const defaults = new Map([
    ['gee-heatmap', { id: 'gee-heatmap', name: 'GEE Heatmap', enabled: false, params: { opacity: 0.78 } }],
    ['boundaries', { id: 'boundaries', name: 'Vector Boundaries', enabled: false, params: { opacity: 0.90 } }],
    ['anomaly-mask', { id: 'anomaly-mask', name: 'Anomaly Mask', enabled: false, params: { opacity: 0.45, threshold: 0.10, palette: 'FF4D6D' } }],
    ['ai-imagery', { id: 'ai-imagery', name: 'AI Imagery Overlay', enabled: false, params: { opacity: 0.65, tile_url: '' } }],
    ['ai-vector', { id: 'ai-vector', name: 'AI Vector Overlay', enabled: false, params: { opacity: 0.90, geojson: null } }],
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
    if (id === 'ai-imagery') {
      if (nextParams.tile_url !== undefined) nextParams.tile_url = String(nextParams.tile_url || '').trim()
      if (nextParams.palette !== undefined) nextParams.palette = String(nextParams.palette || '').trim()
      const thr = Number(nextParams.threshold)
      if (Number.isFinite(thr)) nextParams.threshold = Math.max(0, Math.min(1, thr))
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
          `- Scale: sky`,
          `- Context: ${sc?.id || '—'} (${sc?.targetName || '—'})`,
          q ? `- Intent: ${q}` : `- Intent: ${sc?.label || '—'}`,
          '- Step 1: 调参 LayerTree -> Bloom/Spiral',
          '- Step 2: 高亮星系簇 + 环绕镜头',
        ].join('\n')
        _type(intro)

        await engineRouter.value?.highlightMacroCluster?.()
        await engineRouter.value?.spinMacroCamera?.({ duration: 3.0, revolutions: 1.0 })
        theaterReport.value = [
          'Sky brief:',
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
  const hasContextFromUrl = !!String(_contextFromUrl || '').trim()

  // Patch 0303: keep Global Standby for blank workbench; when entering with a
  // specific ?context=, do a short standby then auto-dive to keep visuals+data
  // in sync.
  try {
    engineRouter.value?.startGlobalStandby?.()
  } catch (_) {
    // ignore
  }

  if (hasContextFromUrl && !_autoDiveDone.value) {
    _autoDiveDone.value = true
    if (_autoDiveTimer) {
      clearTimeout(_autoDiveTimer)
      _autoDiveTimer = null
    }
    _autoDiveTimer = setTimeout(() => {
      try {
        engineRouter.value?.stopGlobalStandby?.()
      } catch (_) {
        // ignore
      }
      _flyToScenario()
    }, 1200)
  }

  // Default should always start with swipe off (reset split state).
  _applySwipeToEngine()
}

const _autoDiveDone = ref(false)
let _autoDiveTimer = null

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

function openCommandPalette() {
  try {
    copilotPanel.value?.openPalette?.()
  } catch (_) {
    // ignore
  }
}

function onCopilotSubmit(text) {
  ;(async () => {
    const q = String(text || '').trim()
    if (!q) return
    if (executeBusy.value) return

    try {
      lastIntent.value = q
      window.sessionStorage?.setItem?.('z2x:lastIntent', lastIntent.value)
    } catch (_) {
      // ignore
    }

    // Append user message (no single-state overwrite).
    try {
      chatHistory.value = [
        ...(chatHistory.value || []),
        { id: `u:${Date.now()}`, role: 'user', content: q },
      ]
    } catch (_) {
      // ignore
    }

    executeBusy.value = true

    // Ask backend to produce a deterministic tool-calling plan (v7 stub).
    try {
      const resp = await apiService.executeCopilot(lastIntent.value, {
        context_id: contextId.value,
        scale: researchStore.currentScale.value,
      })
      const events = Array.isArray(resp?.events) ? resp.events : []
      copilotEvents.value = events
      applyCopilotEvents(events)

      // Patch update: avoid blank output when backend doesn't emit events.final.
      // Prefer explicit reply/text fields, then fallback to events.final.
      let finalText = ''
      try {
        finalText = String(resp?.reply || resp?.text || '').trim()
      } catch (_) {
        finalText = ''
      }
      if (!finalText) {
        try {
          const finalEv = events.find((e) => e && typeof e === 'object' && e.type === 'final')
          finalText = String(finalEv?.text || finalEv?.content || '').trim()
        } catch (_) {
          finalText = ''
        }
      }

      const safeAssistantText = finalText || '空间计算任务已执行完成，请查看左侧面板或右侧思维链。'
      if (finalText) theaterReport.value = finalText

      try {
        chatHistory.value = [
          ...(chatHistory.value || []),
          { id: `a:${Date.now()}`, role: 'assistant', content: safeAssistantText, events },
        ]
      } catch (_) {
        // ignore
      }

      try {
        agentText.value = ''
      } catch (_) {
        // ignore
      }
    } catch (e) {
      copilotEvents.value = []
      try {
        chatHistory.value = [
          ...(chatHistory.value || []),
          { id: `a:${Date.now()}`, role: 'assistant', content: `Backend error: ${e?.message || String(e)}`, events: [] },
        ]
      } catch (_) {
        // ignore
      }
    } finally {
      executeBusy.value = false
    }
  })()
}

function applyCopilotEvents(events) {
  const arr = Array.isArray(events) ? events : []

  // Phase 1 (v7.1): tool-calling events must write deterministic artifacts.
  try {
    const next = applyCopilotArtifacts(
      {
        layers: layers.value,
        charts: charts.value,
        code: code.value,
        report: theaterReport.value,
      },
      arr
    )
    if (next && typeof next === 'object') {
      if (Array.isArray(next.layers)) layers.value = next.layers
      if (Array.isArray(next.charts)) charts.value = next.charts
      if (typeof next.code === 'string') code.value = next.code
      if (typeof next.report === 'string') theaterReport.value = next.report
    }
  } catch (_) {
    // ignore
  }

  for (const e of arr) {
    if (e?.type !== 'tool_call') continue
    const tool = String(e?.tool || '').trim()
    const args = (e && typeof e === 'object') ? e.args : null

    if (tool === 'switch_scale') {
      const target = String(args?.target || '').trim().toLowerCase()
      if (target) setScale(target)
      continue
    }

    if (tool === 'enable_swipe_mode') {
      const posArg = Number(args?.position)
      swipeEnabled.value = true
      swipePosition.value = Number.isFinite(posArg) ? Math.max(0, Math.min(1, posArg)) : 0.5

      _applySwipeToEngine()
      continue
    }

    if (tool === 'set_swipe_position') {
      const posArg = Number(args?.position)
      if (Number.isFinite(posArg)) swipePosition.value = Math.max(0, Math.min(1, posArg))
      try {
        engineRouter.value?.setSwipePosition?.(swipePosition.value)
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'disable_swipe_mode') {
      swipeEnabled.value = false
      _applySwipeToEngine()
      continue
    }

    if (tool === 'camera_fly_to' || tool === 'fly_to') {
      const lat = Number(args?.lat)
      const lon = Number(args?.lon)
      if (Number.isFinite(lat) && Number.isFinite(lon)) {
        const heightArg = Number(args?.height)
        const durationArg = Number(args?.duration_s)
        const headingArg = Number(args?.heading_deg)
        const pitchArg = Number(args?.pitch_deg)
        const height = Number.isFinite(heightArg) ? heightArg : 1800000
        const duration = Number.isFinite(durationArg) ? durationArg : 3.6
        const heading = Number.isFinite(headingArg) ? headingArg : 0
        const pitch = Number.isFinite(pitchArg) ? pitchArg : -55

        // Leaving standby: stop the global orbit and dive to target.
        try {
          engineRouter.value?.stopGlobalStandby?.()
        } catch (_) {
          // ignore
        }

        // Map known demo coords to an existing scenario context.
        if (!String(contextId.value || '').trim()) {
          if (lat < 0) contextId.value = 'amazon'
          else if (lat > 25 && lon > 110) contextId.value = 'yuhang'
          else if (lat > 35 && lon > 100 && lon < 120) contextId.value = 'maowusu'
        }

        // Persist context so UI/URL doesn't appear to "jump back".
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

        // Cinematic-ish default: high-altitude oblique view.
        try {
          engineRouter.value?.flyToLocation?.(
            { lat, lon, height, heading_deg: heading, pitch_deg: pitch, easing: 'cubicinout' },
            duration
          )
        } catch (_) {
          // ignore
        }
      }
      continue
    }

    if (tool === 'aef_compute_diff') {
      // Ensure anomaly visualization is enabled.
      try {
        layers.value = (layers.value || []).map((l) => {
          if (l.id === 'anomaly-mask') return { ...l, enabled: true }
          if (l.id === 'gee-heatmap') return { ...l, enabled: true }
          return l
        })
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'enable_3d_terrain') {
      try {
        void engineRouter.value?.enable3DTerrain?.(args || {})
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'add_cesium_3d_tiles') {
      try {
        void engineRouter.value?.addCesium3DTiles?.(args || {})
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'set_scene_mode') {
      try {
        engineRouter.value?.setSceneMode?.(args?.mode)
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'play_czml_animation') {
      try {
        void engineRouter.value?.playCzmlAnimation?.(args || {})
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'set_globe_transparency') {
      try {
        engineRouter.value?.setGlobeTransparency?.(args?.alpha)
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'enable_subsurface_mode') {
      // v7.2 Demo 12: translucent globe + collision disabled + best-effort dive.
      try {
        engineRouter.value?.stopGlobalStandby?.()
      } catch (_) {
        // ignore
      }
      try {
        engineRouter.value?.enableSubsurfaceMode?.({
          transparency: args?.transparency,
          target_depth_meters: args?.target_depth_meters,
        })
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'disable_subsurface_mode') {
      try {
        engineRouter.value?.disableSubsurfaceMode?.()
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'add_subsurface_model') {
      try {
        void engineRouter.value?.addSubsurfaceModel?.(args || {})
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'execute_dynamic_wgsl') {
      // v7.2 Demo 13: write WGSL into editor + run WebGPU overlay sandbox.
      const wgsl = String(args?.wgsl_compute_shader || '').trim()
      if (wgsl) {
        try {
          code.value = wgsl
        } catch (_) {
          // ignore
        }
        // Prefer Lab so the editor is visible when available.
        try {
          if (String(mode.value || '') === 'theater') setMode('lab')
        } catch (_) {
          // ignore
        }
        try {
          ensureTabKind('twin')
        } catch (_) {
          // ignore
        }
      }

      try {
        void engineRouter.value?.executeDynamicWgsl?.({
          wgsl_compute_shader: wgsl,
          particle_count: args?.particle_count,
        })
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'destroy_webgpu_sandbox') {
      try {
        engineRouter.value?.destroyWebGpuSandbox?.()
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'add_cesium_water_polygon') {
      try {
        void engineRouter.value?.addWaterPolygon?.(args || {})
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'add_cesium_extruded_polygons') {
      try {
        void engineRouter.value?.addExtrudedPolygons?.(args || {})
      } catch (_) {
        // ignore
      }
      continue
    }

    if (tool === 'trigger_gsap_wormhole') {
      // MVR: use the existing macro→micro quantum dive animation.
      // When coming from earth, hop to macro (mount ThreeTwin) then micro.
      const target = String(args?.target || 'micro').trim().toLowerCase() || 'micro'
      if (target === 'micro') {
        try {
          const cur = String(researchStore.currentScale.value || '').trim().toLowerCase()
          if (cur === 'earth') {
            setScale('macro')
            setTimeout(() => {
              try {
                setScale('micro')
              } catch (_) {
                // ignore
              }
            }, 0)
          } else {
            setScale('micro')
          }
        } catch (_) {
          // ignore
        }
      }
      continue
    }

    if (tool === 'generate_molecular_lattice') {
      try {
        void engineRouter.value?.rebuildMicroLattice?.()
      } catch (_) {
        // ignore
      }
      continue
    }
  }
}

function onCopilotSelectPreset(preset) {
  const id = String(preset?.id || '').trim().toLowerCase()
  if (!id) return

  // v7.1 spec: keep an IDE feel by default.
  // Do NOT force Theater/Lab here; users can toggle via top bar / F11.
  ensureTabKind('twin')

  // Deterministic mapping: bind to a stable scenario + scale.
  // Prefer explicit ids, but also support keyword contains for backward compat.
  const setContextScale = (ctx, scale) => {
    if (ctx) contextId.value = String(ctx)
    if (scale) setScale(String(scale))
  }

  if (id === 'demo:yuhang_audit' || id.includes('yuhang')) setContextScale('yuhang', 'earth')
  else if (id === 'demo:amazon_cluster' || id.includes('amazon')) setContextScale('amazon', 'earth')
  else if (id === 'demo:maowusu_cos' || id.includes('maowusu')) setContextScale('maowusu', 'earth')
  else if (id.includes('yancheng')) setContextScale('yancheng', 'earth')
  else if (id.includes('zhoukou')) setContextScale('zhoukou', 'earth')
  else if (id.includes('nyc') || id.includes('newyork')) setContextScale('nyc', 'earth')
  else if (id.includes('congo')) setContextScale('congo', 'earth')
  else if (id.includes('malacca')) setContextScale('malacca', 'earth')
  else if (id.includes('pilbara')) setContextScale('pilbara', 'earth')
  else if (id.includes('everest')) setContextScale('everest_lake', 'earth')
  else if (id.includes('mauna')) setContextScale('mauna_loa', 'earth')
  else if (id.includes('talatan')) setContextScale('talatan', 'earth')
  else if (id.includes('wind') || id.includes('gfs') || id.includes('glsl')) setContextScale('global', 'earth')
  else if (id.includes('wormhole') || id.includes('micro')) setContextScale(contextId.value || 'poyang', 'micro')

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
}

function applyPreset(preset) {
  const p = preset || {}
  const nextContext = String(p.contextId || '').trim().toLowerCase()
  if (nextContext) contextId.value = nextContext

  // Preserve user-selected Lab/Theater mode (do not force mode from preset).

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
    openCommandPalette()
    return
  }
  if (k === 'escape') {
    try {
      copilotPanel.value?.closePalette?.()
    } catch (_) {
      // ignore
    }
  }
}

watch(
  () => scenario.value?.id,
  () => {
    code.value = buildCodeStub(scenario.value)
  }
)

watch(
  () => swipeEnabled.value,
  () => {
    // Enabling swipe should deterministically pick sane ids and ensure layers
    // are visible; disabling should reset split state.
    _applySwipeToEngine()
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

    // Swipe is an Earth-only spatial mode; reset when leaving earth.
    try {
      const cur = String(researchStore.currentScale.value || '').trim().toLowerCase()
      if (cur !== 'earth' && swipeEnabled.value) {
        swipeEnabled.value = false
        _applySwipeToEngine()
      }
    } catch (_) {
      // ignore
    }
  }
)

watch(
  () => swipePosition.value,
  () => {
    if (!swipeEnabled.value) return
    try {
      engineRouter.value?.setSwipePosition?.(swipePosition.value)
    } catch (_) {
      // ignore
    }
  }
)

watch(
  () => scenario.value?.id,
  () => {
    // Changing context should not keep a split from previous compare.
    if (!swipeEnabled.value) return
    swipeEnabled.value = false
    _applySwipeToEngine()
  }
)

watch(
  () => scenario.value?.id,
  (newId, oldId) => {
    if (!newId || newId === oldId) return
    if (!viewerReady.value) return

    // Patch update: presets may not emit fly_to; force one on scenario change.
    setTimeout(() => {
      try {
        engineRouter.value?.stopGlobalStandby?.()
        engineRouter.value?.flyToScenario?.()
      } catch (_) {
        // ignore
      }
    }, 100)
  }
)

onMounted(() => {
  try {
    document.body.style.overflow = 'hidden'
  } catch (_) {
    // ignore
  }

  window.addEventListener('keydown', onKeydown)

  ;(async () => {
    try {
      const prompts = await apiService.listCopilotPrompts()
      if (Array.isArray(prompts) && prompts.length) {
        copilotPresets.value = prompts
      }
    } catch (_) {
      // ignore (keep local defaults)
    }
  })()

  try {
    // contextId/currentScale are initialized synchronously during setup to avoid
    // mount-then-unmount races. Here we only restore secondary UI state.

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
      // UX: keep these heavy / diagnostic overlays unchecked by default.
      // This is applied on restore as well to avoid surprising users.
      const forceOff = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask', 'ai-vector'])
      layers.value = (layersParsed || []).map((l) => (forceOff.has(String(l?.id || '')) ? { ...l, enabled: false } : l))
    }

    lastIntent.value = window.sessionStorage?.getItem?.('z2x:lastIntent') || ''
    window.sessionStorage?.setItem?.('z2x:lastContext', contextId.value)
  } catch (_) {
    lastIntent.value = ''
  }

  // Golden path: auto-play a short demo when arriving from Act2.
  // Keep workbench quiet by default; only auto-run when explicitly requested.
  if (_autoplayFromUrl || _contextFromUrl) {
    setTimeout(() => runStub(), 220)
  }
})

onBeforeUnmount(() => {
  _stop()
  _stopTimeline()
  if (_autoDiveTimer) {
    clearTimeout(_autoDiveTimer)
    _autoDiveTimer = null
  }
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

.pointer-events-none {
  pointer-events: none;
}

.pointer-events-auto {
  pointer-events: auto;
}

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
  justify-content: flex-start;
  gap: 18px;
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
  position: relative;
  overflow: hidden;
}

.top-nav::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  padding: 1px;
  background: linear-gradient(90deg, rgba(0, 240, 255, 0.55), rgba(120, 160, 255, 0.22), rgba(0, 240, 255, 0.45));
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.55;
  pointer-events: none;
}

.top-nav::after {
  content: '';
  position: absolute;
  top: 0;
  left: -40%;
  height: 100%;
  width: 30%;
  background: linear-gradient(90deg, rgba(0, 0, 0, 0), rgba(0, 240, 255, 0.12), rgba(0, 0, 0, 0));
  transform: skewX(-18deg);
  animation: hud-scan 7s linear infinite;
  opacity: 0.35;
  pointer-events: none;
}

@keyframes hud-scan {
  0% {
    transform: translateX(-120%) skewX(-18deg);
  }
  100% {
    transform: translateX(520%) skewX(-18deg);
  }
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

.left-rail {
  width: 360px;
  flex-shrink: 0;
  padding: 12px;
  overflow: hidden;
}

.center-stage {
  flex: 1;
  min-width: 0;
  position: relative;
  /* Let pointer events fall through to the engine canvas behind.
     Interactive center panels (table/charts/status) explicitly opt-in. */
  pointer-events: none;
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

.right-rail {
  width: 400px;
  flex-shrink: 0;
  padding: 12px;
  overflow: hidden;
}


.timeline-float {
  position: absolute;
  left: 50%;
  bottom: 28px;
  transform: translateX(-50%);
  width: min(640px, calc(100vw - 64px));
  padding: 10px 12px;
  border-radius: 16px;
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
  .left-rail {
    width: 320px;
  }
  .right-rail {
    width: 360px;
  }
}

@media (max-width: 860px) {
  .middle-workspace {
    flex-direction: column;
  }
  .left-rail,
  .right-rail {
    width: 100%;
  }
}
</style>
