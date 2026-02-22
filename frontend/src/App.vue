<template>
  <div class="app-container">
    <CesiumViewer
      ref="cesiumViewer"
      :initial-location="initialLocation"
      @viewer-ready="onViewerReady"
      @map-center-changed="onMapCenterChanged"
    />

    <!-- Debug HUD: map screen-center coordinates (bottom-left) -->
    <div v-if="viewerReady" class="debug-center">
      CENTER: {{ mapCenterText }}
    </div>

    <!-- Global exit: Abort & Orbit -->
    <transition name="slide-down">
      <button
        v-if="appState !== 'standby'"
        class="abort-btn"
        :disabled="!viewerReady"
        @click="abortAndOrbit"
        title="清理图层并返回全球轨道视角"
      >
        Abort & Orbit
      </button>
    </transition>

    <!-- Act 1: Orbit Lobby (mission-only interaction) -->
    <transition name="fade-up">
      <div v-if="appState === 'standby'" class="lobby">
        <div class="lobby-hero">
          <div class="hero-title">ALPHA EARTH</div>
          <div class="subtitle">场景验证系统</div>
          <div class="lobby-hint">
            点击任务包，智能体将自动锁定目标并展开研判。
          </div>
        </div>

        <div class="mission-deck">
          <div class="deck-title">行星级任务包（Missions）</div>
          <div v-if="!missions?.length" class="mission-empty">正在加载 Missions…</div>

          <div class="mission-row">
            <button
              v-for="m in missions"
              :key="m.id"
              class="mission-card"
              @click="lockMission(m)"
              :disabled="!viewerReady"
            >
              <div class="mission-card-top">
                <span class="tag">{{ getChapterCode(m.id) || m.name }}</span>
                <span class="tag secondary">{{ locations?.[m.location]?.name || m.location }}</span>
                <span v-if="m.formula" class="tag tertiary formula">{{ m.formula }}</span>
              </div>
              <div class="mission-card-title">{{ m.title }}</div>
              <div class="mission-card-foot">
                <span class="dot" :class="prefetchState[m.id]?.ok ? 'ok' : (prefetchState[m.id]?.done ? 'bad' : 'idle')"></span>
                <span class="foot-text">
                  <template v-if="prefetchState[m.id]?.done">
                    {{ prefetchState[m.id]?.ok ? '预热完成' : '预热失败（仍可点击执行）' }}
                  </template>
                  <template v-else>
                    {{ viewerReady ? '待机中：后台静默预热' : '地球引擎初始化中…' }}
                  </template>
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Act 3: Agentic Analysis Console -->
    <transition name="slide-left">
      <div v-if="appState === 'analyzing'" class="ai-panel" ref="aiPanelEl">
        <div class="ai-header">
          <div class="ai-title-row">
            <div class="ai-title">ALPHA EARTH <span>INTEL</span></div>
            <div class="ai-actions">
              <button class="ai-btn" @click="toggleAILayer" :disabled="!viewerReady" title="开关 AI 叠加图层（不重新加载瓦片）">
                AI Layer: {{ aiLayerVisible ? 'ON' : 'OFF' }}
              </button>
              <button class="ai-btn" @click="toggleSplitCompare" :disabled="!viewerReady" title="开启分屏滑杆对比（左底图/右AI）">
                Swipe: {{ splitCompareEnabled ? 'ON' : 'OFF' }}
              </button>
              <button
                class="ai-btn secondary"
                :class="{ active: holdingCompare }"
                @pointerdown.prevent="beginHoldCompare"
                @pointerup.prevent="endHoldCompare"
                @pointercancel.prevent="endHoldCompare"
                @pointerleave.prevent="endHoldCompare"
                :disabled="!viewerReady"
                title="按住临时隐藏 AI 图层以便对比"
              >
                Hold Compare
              </button>
            </div>
          </div>
          <div class="ai-sub">
            <span class="k">MISSION</span>
            <span class="v">{{ currentMission?.name || '—' }}</span>
            <span class="sep">///</span>
            <span class="k">TARGET</span>
            <span class="v">{{ currentTargetName }}</span>
          </div>
          <div class="ai-status" :class="statusType">
            <span class="badge">{{ isCached ? 'ASSET' : 'CLOUD' }}</span>
            <span class="msg">{{ statusMsg }}</span>
          </div>
        </div>

        <div class="ai-body">
          <div class="commander-panel">
            <div class="ai-section-title">指挥官面板</div>

            <div class="cmd-block">
              <div class="cmd-label">业务简报（Brief）</div>
              <div class="cmd-text">{{ commanderBrief?.brief || '—' }}</div>
            </div>

            <div class="cmd-block">
              <div class="cmd-label">是什么（机理一句话）</div>
              <div class="cmd-text">{{ commanderBrief?.mechanism || '—' }}</div>
            </div>

            <div v-if="commanderBrief?.legends?.length" class="cmd-block">
              <div class="cmd-label">在哪看（图例）</div>
              <div class="cmd-legends">
                <div v-for="(l, idx) in commanderBrief.legends" :key="idx" class="cmd-legend">
                  <span class="cmd-swatch" :style="{ background: l.color }"></span>
                  <span class="cmd-legend-label">{{ l.label }}</span>
                </div>
              </div>
              <div v-if="legendHint" class="cmd-hint">{{ legendHint }}</div>
            </div>

            <div class="cmd-block">
              <div class="cmd-label">怎么办（1–2 条洞察）</div>
              <pre class="cmd-insights">{{ insightsText || '—' }}</pre>
            </div>

            <details class="cmd-details">
              <summary>展开完整输出（技术版）</summary>
              <div class="ai-section-title" style="margin-top: 12px;">技术版输出（结构化）</div>
              <pre class="ai-report-box">{{ commanderBrief?.technical || '—' }}</pre>

              <div class="ai-section-title" style="margin-top: 12px;">AI 思考输出（演示版流式）</div>
              <pre class="ai-console">{{ analysisText }}</pre>

              <div v-if="reportText" class="ai-report">
                <div class="ai-section-title">决策简报</div>
                <pre class="ai-report-box">{{ reportText }}</pre>
              </div>
            </details>
          </div>
        </div>
      </div>
    </transition>

    <!-- Swipe Compare slider overlay (drag ONLY on handle; does not block AI panel clicks) -->
    <div v-if="appState === 'analyzing' && splitCompareEnabled" class="split-compare">
      <div class="split-line" :style="{ left: (splitPosition * 100) + '%' }">
        <div
          class="split-handle"
          title="拖动把手以对比"
          @pointerdown.stop.prevent="onSplitHandleDown"
        ></div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import CesiumViewer from './components/CesiumViewer.vue'
import { apiService } from './services/api.js'
import { formatLatLon } from './utils/coords.js'
import {
  buildCommanderBrief,
  buildLegendHint,
  extractActionInsightsFromReport,
  getChapterCode,
} from './utils/missionBrief.js'

export default {
  name: 'App',
  components: {
    CesiumViewer
  },
  
  setup() {
    const cesiumViewer = ref(null)
    const aiPanelEl = ref(null)
    const locations = ref({})
    const modes = ref({})
    const missions = ref([])
    const viewerReady = ref(false)

    // Narrative state machine
    // standby: global rotation | flying: target lock dive | analyzing: show HUD + panel
    const appState = ref('standby')
    const selectedMissionId = ref(null)
    const selectedLocation = ref(null)
    const selectedMode = ref('')
    const isCached = ref(false)
    const perfStats = ref(null)
    const zonalStats = ref(null)
    const reportText = ref('')

    // Commander panel (leader-friendly)
    const commanderBrief = ref(null) // { mechanism, legends, insights }
    const insightsText = ref('')
    let insightsTimer = null

    const legendHint = computed(() => {
      return buildLegendHint(commanderBrief.value?.legends)
    })

    // Silent prefetch state
    const prefetchState = ref({}) // { [missionId]: { done: bool, ok: bool, ms: number } }
    const prefetchedLayers = ref({}) // { [missionId]: layerData }
    const prefetchStarted = ref(false)

    // Typewriter / analysis console
    const analysisText = ref('')
    let typeTimer = null
    let runToken = 0

    // Debug: map center coords
    const mapCenter = ref({ lat: null, lon: null, ts: null })
    const mapCenterText = computed(() => {
      return formatLatLon(mapCenter.value?.lat, mapCenter.value?.lon, 5)
    })

    // AI layer compare controls
    const aiLayerVisible = ref(true)
    const holdingCompare = ref(false)

    // Split / swipe compare
    const splitCompareEnabled = ref(false)
    const splitPosition = ref(0.5)
    const draggingSplit = ref(false)
    const splitMinPos = ref(0.02)
    const splitMaxPos = ref(0.98)

    // Remember the last successfully loaded AI layer so we can detach it (stop tile requests)
    // and later restore it without re-hitting /api/layers.
    const lastAiTileUrl = ref('')
    const lastAiOpacity = ref(0.88)

    // Old version behavior: no managed Sentinel-2 basemap overlay by default.
    // Keep the feature behind an env flag so the globe doesn't get a "mask layer"
    // when users think they've turned AI off.
    const sentinelBasemapEnabled = (import.meta.env.VITE_ENABLE_SENTINEL_BASEMAP === '1')

    function _onResize() {
      if (appState.value !== 'analyzing') return
      if (!splitCompareEnabled.value) return

      _recalcSplitBounds()
      splitPosition.value = Math.min(splitMaxPos.value, Math.max(splitMinPos.value, splitPosition.value))
      try {
        cesiumViewer.value?.setSplitPosition?.(splitPosition.value)
      } catch (_) {
        // ignore
      }
    }

    // Status box
    const statusMsg = ref('系统待机中...')
    const statusType = ref('idle') // idle | loading | success | error
    const loading = ref(false)

    const currentMission = computed(() => {
      if (!selectedMissionId.value) return null
      return missions.value.find((m) => m.id === selectedMissionId.value) || null
    })
    
    const currentLocationData = computed(() => {
      if (!selectedLocation.value) return null
      return locations.value[selectedLocation.value]
    })

    const currentTargetName = computed(() => {
      return currentLocationData.value?.name || '—'
    })
    
    const initialLocation = computed(() => {
      // Start from a global view (planetary base). We will dive to target after selection.
      return { lat: 35.0, lon: 105.0, height: 20000000 }
    })
    
    onMounted(async () => {
      try {
        // 加载地点/模式/Missions 列表
        const [locs, ms, missionsData] = await Promise.all([
          apiService.getLocations(),
          apiService.getModes(),
          apiService.getMissions()
        ])
        locations.value = locs
        modes.value = ms
        missions.value = missionsData
      } catch (error) {
        console.error('初始化失败:', error)
        alert('后端连接失败：请确保 API 服务已启动（默认端口 8505），且前端 /api 代理可用。')
      }

      // keep split bounds in sync with responsive right panel
      try {
        window.addEventListener('resize', _onResize, { passive: true })
      } catch (_) {
        // ignore
      }
    })

    onBeforeUnmount(() => {
      _stopTypewriter()
      _stopInsightsTypewriter()
      _removeSplitDragListeners()
      try {
        window.removeEventListener('resize', _onResize)
      } catch (_) {
        // ignore
      }
    })
    
    async function onViewerReady(viewer) {
      viewerReady.value = true
      // Act 1: start global rotation when viewer is ready
      try {
        cesiumViewer.value?.startGlobalRotation?.()
      } catch (_) {
        // ignore
      }

      // Silent prefetch in orbit lobby (warm GEE compute + tile registry)
      // Do not block UI; best-effort only.
      try {
        setTimeout(() => {
          silentPrefetchMissions()
        }, 700)
      } catch (_) {
        // ignore
      }
    }

    function onMapCenterChanged(payload) {
      if (!payload) return
      mapCenter.value = {
        lat: payload.lat,
        lon: payload.lon,
        ts: payload.ts || Date.now()
      }
    }

    function normalizeTileUrl(url) {
      if (!url || typeof url !== 'string') return url
      const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8505'
      if (url.startsWith(apiBase + '/')) {
        return url.slice(apiBase.length)
      }
      return url
    }

    async function ensureBasemapForLocation(locationCode) {
      if (!viewerReady.value || !cesiumViewer.value) return
      if (!locationCode) return
      if (!sentinelBasemapEnabled) return

      try {
        const resp = await apiService.getSentinel2Layer(locationCode)
        const url = normalizeTileUrl(resp?.tile_url)
        if (url) {
          cesiumViewer.value?.loadBasemapLayer?.(url, 1.0)
        }
      } catch (_) {
        // Best-effort only. If Sentinel-2 fails, Ion/OSM/Grid remains underneath.
      }
    }

    function lockMission(mission) {
      if (!viewerReady.value) return
      selectedMissionId.value = mission.id
      selectedLocation.value = mission.location
      selectedMode.value = mission.api_mode
      runToken += 1
      appState.value = 'flying'
      statusType.value = 'idle'
      statusMsg.value = '目标锁定，正在俯冲...'
      isCached.value = false
      perfStats.value = null
      zonalStats.value = null
      reportText.value = ''
      analysisText.value = ''
      _stopTypewriter()
      commanderBrief.value = null
      insightsText.value = ''
      _stopInsightsTypewriter()
      aiLayerVisible.value = true
      holdingCompare.value = false
      splitCompareEnabled.value = false
      splitPosition.value = 0.5
      draggingSplit.value = false

      try {
        cesiumViewer.value?.stopGlobalRotation?.()
      } catch (_) {
        // ignore
      }

      try {
        cesiumViewer.value?.clearAILayer?.()
      } catch (_) {
        // ignore
      }

      try {
        cesiumViewer.value?.clearBasemapLayer?.()
      } catch (_) {
        // ignore
      }

      const loc = locations.value?.[mission.location]
      const locCoords = Array.isArray(loc?.coords) ? loc.coords : null
      const cam = mission.camera || {}

      // Prefer /api/locations coords as the single source of truth.
      // This avoids drift if mission.camera becomes stale.
      const lat = (locCoords && locCoords.length >= 2) ? Number(locCoords[0]) : Number(cam.lat)
      const lon = (locCoords && locCoords.length >= 2) ? Number(locCoords[1]) : Number(cam.lon)
      const height = cam.height || 12000
      const duration = cam.duration_s || 3.5

      cesiumViewer.value?.flyTo?.(
        { lat, lon, height },
        duration,
        () => {
          appState.value = 'analyzing'
          statusType.value = 'idle'
          statusMsg.value = '情报展开：智能体接管中...'
          // Auto-load the default layer for the mission (agentic)
          runAgenticWorkflow(mission)
        }
      )
    }

    function abortAndOrbit() {
      // Global exit: clear layer + reset state + fly back to orbit
      appState.value = 'standby'
      selectedMissionId.value = null
      selectedLocation.value = null
      selectedMode.value = ''
      loading.value = false
      statusType.value = 'idle'
      statusMsg.value = '系统待机中...'
      isCached.value = false
      perfStats.value = null
      zonalStats.value = null
      reportText.value = ''
      analysisText.value = ''
      _stopTypewriter()
      commanderBrief.value = null
      insightsText.value = ''
      _stopInsightsTypewriter()
      aiLayerVisible.value = true
      holdingCompare.value = false
      splitCompareEnabled.value = false
      splitPosition.value = 0.5
      draggingSplit.value = false

      try {
        cesiumViewer.value?.enableSplitCompare?.(false)
      } catch (_) {
        // ignore
      }

      try {
        cesiumViewer.value?.clearAILayer?.()
      } catch (_) {
        // ignore
      }

      try {
        cesiumViewer.value?.clearBasemapLayer?.()
      } catch (_) {
        // ignore
      }

      try {
        // Back to orbit and resume rotation
        cesiumViewer.value?.startGlobalRotation?.()
      } catch (_) {
        // ignore
      }
    }

    function _stopTypewriter() {
      if (typeTimer) {
        clearInterval(typeTimer)
        typeTimer = null
      }
    }

    function _typewriterAppend(text, speedMs = 16) {
      _stopTypewriter()
      let idx = 0
      typeTimer = setInterval(() => {
        if (idx >= text.length) {
          _stopTypewriter()
          return
        }
        analysisText.value += text[idx]
        idx += 1
      }, Math.max(8, speedMs))
    }

    function _stopInsightsTypewriter() {
      if (insightsTimer) {
        clearInterval(insightsTimer)
        insightsTimer = null
      }
    }

    function _typewriterSetInsights(text, speedMs = 16, tokenSnapshot = runToken) {
      _stopInsightsTypewriter()
      insightsText.value = ''
      let idx = 0
      insightsTimer = setInterval(() => {
        if (tokenSnapshot !== runToken) {
          _stopInsightsTypewriter()
          return
        }
        if (idx >= text.length) {
          _stopInsightsTypewriter()
          return
        }
        insightsText.value += text[idx]
        idx += 1
      }, Math.max(10, speedMs))
    }

    function _renderAnalysisSections({ mission, modeName, stats }) {
      const total = stats?.total_area_km2
      const anomaly = stats?.anomaly_area_km2
      const pct = stats?.anomaly_pct

      const fmt = (x, d = 2) => {
        if (x === null || x === undefined) return '—'
        const n = Number(x)
        if (Number.isNaN(n)) return String(x)
        return n.toFixed(d)
      }

      // NOTE: This is a DEMO "thinking log" for narrative effect.
      // It is not an actual chain-of-thought from the LLM.
      const algo = _getAlgorithmExplanation(selectedMode.value, mission)

      const observation =
        `【异动感知 Observation】\n` +
        `- 任务：${mission?.title || '—'}\n` +
        `- 算法：${modeName || '—'} (${mission?.formula || '—'})\n` +
        `- 统计：总面积 ${fmt(total)} km²；异常面积 ${fmt(anomaly)} km²；异常占比 ${fmt(pct)}%\n\n`

      const algorithm =
        `【算法逻辑 Algorithm】\n` +
        `${algo}\n\n`

      const reasoning =
        `【归因分析 Reasoning】\n` +
        `- 对高维特征场进行空间一致性检验，排除局部噪声与边界伪影。\n` +
        `- 若异常呈连片分布，优先判定为结构性变化；若零散点状，优先排查云/阴影/季节扰动。\n\n`

      const action =
        `【行动建议 Action】\n` +
        `- 将异常占比高的网格列为优先核查清单，并联动 Sentinel-2 影像做目视复核。\n` +
        `- 对持续热点区域建议开展跨期对比，输出“处置-复核-闭环”台账。\n`

      const consensus =
        `\n【共识印证 Consensus】\n` +
        `- 本次研判通过统一表征隐空间的量化信号，为“事件叙事”提供可复核的证据锚点。\n` +
        `- 建议将热点边界与统计结果用于对外沟通与跨部门复核，避免把季节/云影误判为成果或风险。\n`

      return (
        `AEF/AGENT v6 :: Mission Accepted\n` +
        `----------------------------------------\n\n` +
        observation + algorithm + reasoning + action + consensus
      )
    }

    function _getAlgorithmExplanation(modeId, mission) {
      const common =
        `- 输入：Google AEF/Embedding 年度特征（64 维语义向量）。输出：一张“异常/强度/韧性”的空间热区图 + 面积统计。\n` +
        `- 生成：filterBounds(viewport)+mosaic() 做全视锥拼接；阈值后用 updateMask() 只保留“值得看的像元”；reduceRegion 产出可汇报指标（km²/占比）。\n` +
        `- 速度：smart_load 优先命中预计算 Asset；瓦片同源代理 + 内存 LRU 缓存，保证拖动/缩放不反复打上游。\n`

      if (modeId === 'ch1_yuhang_faceid') {
        return (
          common +
          `- 第一章·欧氏距离：计算跨期语义距离 $||V_{2017}-V_{2024}||_2$，阈值后仅显示“结构性突变”像元。\n` +
          `  - 直观含义：城市硬化地表、功能区重写会在隐空间产生显著位移，可作为“城建审计”的量化抓手。\n`
        )
      }
      if (modeId === 'ch2_maowusu_shield') {
        return (
          common +
          `- 第二章·余弦相似度：关注向量方向而非幅度，降低季节性振幅扰动影响；将 $1-\cos(\theta)$ 作为风险得分。\n` +
          `  - 共识印证：哪怕在秋冬枯黄季节，算法仍能从“语义骨骼”层面确认固沙林已成型，用于粉碎“伪绿化”的质疑。\n`
        )
      }
      if (modeId === 'ch3_zhoukou_pulse') {
        return (
          common +
          `- 第三章·特定维度反演：抽取对农田结构/胁迫敏感的特定维度（示意：A02），归一化后生成可解释的强度场。\n` +
          `  - 用途：在“看上去都很绿”的麦田中，提前识别内涝/缺氧/倒伏等风险网格，支持粮仓体检与预警。\n`
        )
      }
      if (modeId === 'ch4_amazon_zeroshot') {
        return (
          common +
          `- 第四章·零样本聚类：不提供先验标签，直接对隐空间做 K-Means（示意：k=6），自动切分结构单元。\n` +
          `  - 工程保障：训练样本限定在 training_region（硬编码小缓冲区），避免全域无监督导致 GEE Timeout。\n`
        )
      }
      if (modeId === 'ch5_coastline_audit') {
        return (
          common +
          `- 第五章·海岸线红线审计：抽取 A00/A02 低维语义特征做 K-Means（示意：k=3），将海岸线结构/占用带做快速聚类分区。\n` +
          `  - 工程保障：训练样本限定在盐城沿海的小矩形 training_region，避免“全视口训练”导致 GEE 计算超时。\n` +
          `  - 解读建议：将聚类结果与自然岸线/围垦边界/工程岸线矢量叠加，形成“红线核查清单”。\n`
        )
      }
      if (modeId === 'ch6_water_pulse') {
        return (
          common +
          `- 第六章·水网脉动：对水体相关维度（示意：A02）做跨年差分 $\Delta A02 = A02_{2024}-A02_{2022}$，并用 $|\Delta|>0.10$ 掩膜突出显著变化带。\n` +
          `  - 直观含义：丰枯水位差、支汊连通性与湿地边界波动，会在隐空间维度上形成可追踪的差分信号。\n`
        )
      }
      return common + `- 任务算子：${mission?.formula || '—'}（演示模式说明）。\n`
    }

    async function silentPrefetchMissions() {
      if (prefetchStarted.value) return
      if (!viewerReady.value) return
      if (!missions.value?.length) return

      prefetchStarted.value = true

      for (const m of missions.value) {
        const start = Date.now()
        try {
          const layerData = await apiService.getLayer(m.api_mode, m.location)
          prefetchedLayers.value[m.id] = layerData
          prefetchState.value[m.id] = { done: true, ok: true, ms: Date.now() - start }
        } catch (e) {
          prefetchState.value[m.id] = { done: true, ok: false, ms: Date.now() - start }
        }
        // throttle: reduce GEE API burst
        await new Promise((r) => setTimeout(r, 450))
      }
    }

    async function runAgenticWorkflow(mission) {
      if (!mission) return
      if (!selectedLocation.value || !selectedMode.value) return
      if (!viewerReady.value || !cesiumViewer.value) return

      const myToken = runToken

      const modeId = selectedMode.value
      const modeName = modes.value?.[modeId] || modeId
      loading.value = true
      statusType.value = 'loading'
      statusMsg.value = `正在部署 [${modeName}] 图层…`

      const startTs = Date.now()

      try {
        // Optional: managed Sentinel-2 basemap overlay (opt-in; old_version kept Cesium default).
        // Do not block the AI layer on basemap readiness.
        if (sentinelBasemapEnabled && aiLayerVisible.value) {
          try {
            ensureBasemapForLocation(selectedLocation.value)
          } catch (_) {
            // ignore
          }
        }

        const cachedLayer = prefetchedLayers.value?.[mission.id]
        const layerData = cachedLayer || (await apiService.getLayer(modeId, selectedLocation.value))
        if (myToken !== runToken) return
        const url = normalizeTileUrl(layerData.tile_url)
        const hintedOpacity = Number(layerData?.render_hints?.ai_opacity)
        const opacity = Number.isFinite(hintedOpacity) ? hintedOpacity : 0.88

        lastAiTileUrl.value = url
        lastAiOpacity.value = opacity

        cesiumViewer.value.loadAILayer(url, opacity, { fadeIn: true })
        try {
          cesiumViewer.value?.setAILayerVisible?.(aiLayerVisible.value)
        } catch (_) {
          // ignore
        }

        try {
          if (splitCompareEnabled.value) {
            cesiumViewer.value?.enableSplitCompare?.(true, splitPosition.value)
          }
        } catch (_) {
          // ignore
        }

        isCached.value = !!layerData.is_cached
        perfStats.value = { loadTime: Date.now() - startTs }
        statusType.value = 'success'
        statusMsg.value = `✅ [${modeName}] 图层就绪`

        // Show a stable placeholder to avoid the console "restarting" multiple times.
        analysisText.value =
          `AEF/AGENT v6 :: Mission Accepted\n` +
          `----------------------------------------\n\n` +
          `正在生成智能体分析…（将基于统计指标输出 Observation/Reasoning/Plan/Consensus）\n`

        // V5: dynamic zonal stats + brief report
        try {
          const statsResp = await apiService.getStats(modeId, selectedLocation.value)
          if (myToken !== runToken) return
          zonalStats.value = statsResp?.stats || null
        } catch (e) {
          zonalStats.value = null
        }

        // Commander brief: build after stats are available (or null) and stream 1–2 insights.
        try {
          const brief = buildCommanderBrief(modeId, mission, zonalStats.value || null)
          commanderBrief.value = brief
          const insights = Array.isArray(brief?.insights) ? brief.insights.slice(0, 2) : []
          const text = insights.length ? insights.map((s) => `- ${s}`).join('\n') : ''
          if (text) {
            _typewriterSetInsights(text, 14, myToken)
          } else {
            insightsText.value = ''
            _stopInsightsTypewriter()
          }
        } catch (_) {
          commanderBrief.value = null
          insightsText.value = ''
          _stopInsightsTypewriter()
        }

        // Render analysis ONCE (LLM if available, else deterministic local fallback).
        try {
          let finalText = ''
          try {
            const analysisResp = await apiService.getAnalysis(mission.id, zonalStats.value || undefined)
            if (myToken !== runToken) return
            const text = analysisResp?.analysis
            if (text && typeof text === 'string') {
              finalText = text
            }
          } catch (_) {
            // ignore
          }

          if (!finalText) {
            finalText = _renderAnalysisSections({ mission, modeName, stats: zonalStats.value })
          }

          analysisText.value = ''
          _typewriterAppend(finalText, 12)
        } catch (_) {
          // ignore
        }

        try {
          if (zonalStats.value) {
            const reportResp = await apiService.getReport(mission.id, zonalStats.value)
            if (myToken !== runToken) return
            reportText.value = reportResp?.report || ''

            // Prefer report-derived actions (leadership view), fallback remains the brief.
            try {
              const actionItems = extractActionInsightsFromReport(reportText.value, 2)
              if (actionItems?.length) {
                const text = actionItems.map((s) => `- ${s}`).join('\n')
                _typewriterSetInsights(text, 14, myToken)
              }
            } catch (_) {
              // ignore
            }
          } else {
            reportText.value = ''
          }
        } catch (e) {
          reportText.value = ''
        }
      } catch (e) {
        statusType.value = 'error'
        statusMsg.value = `❌ 执行失败: ${e?.message || String(e)}`
      } finally {
        loading.value = false
      }
    }

    // Tool-mode controls removed in V5 agentic paradigm.

    function toggleAILayer() {
      aiLayerVisible.value = !aiLayerVisible.value

      // If split-compare is ON but AI is OFF, Cesium will show a blank "right side" (looks like a white/black mask).
      // Disable split compare automatically to keep the globe stable.
      if (!aiLayerVisible.value && splitCompareEnabled.value) {
        splitCompareEnabled.value = false
        try {
          cesiumViewer.value?.enableSplitCompare?.(false)
        } catch (_) {
          // ignore
        }
      }

      // OFF: remove the layer entirely to stop any background tile requests (prevents proxy 502 storms).
      if (!aiLayerVisible.value) {
        try {
          cesiumViewer.value?.clearAILayer?.()
        } catch (_) {
          // ignore
        }

        // Also clear the managed basemap overlay so AI-OFF truly returns to the default Cesium base.
        try {
          cesiumViewer.value?.clearBasemapLayer?.()
        } catch (_) {
          // ignore
        }
        return
      }

      // ON: restore the layer from the last tile URL (if any).
      if (aiLayerVisible.value) {
        // Optionally re-apply the managed basemap.
        if (sentinelBasemapEnabled) {
          try {
            ensureBasemapForLocation(selectedLocation.value)
          } catch (_) {
            // ignore
          }
        }

        const url = String(lastAiTileUrl.value || '')
        if (url) {
          try {
            cesiumViewer.value?.loadAILayer?.(url, Number(lastAiOpacity.value) || 0.88, { fadeIn: true })
          } catch (_) {
            // ignore
          }
        } else {
          try {
            cesiumViewer.value?.setAILayerVisible?.(true)
          } catch (_) {
            // ignore
          }
        }
      }
    }

    function beginHoldCompare() {
      holdingCompare.value = true
      try {
        // Hold-to-compare: temporarily hide AI overlay
        cesiumViewer.value?.setAILayerVisible?.(false)
      } catch (_) {
        // ignore
      }
    }

    function endHoldCompare() {
      holdingCompare.value = false
      try {
        cesiumViewer.value?.setAILayerVisible?.(aiLayerVisible.value)
      } catch (_) {
        // ignore
      }
    }

    function toggleSplitCompare() {
      splitCompareEnabled.value = !splitCompareEnabled.value
      _recalcSplitBounds()
      // Clamp current position so the slider stays left of the analysis panel
      splitPosition.value = Math.min(splitMaxPos.value, Math.max(splitMinPos.value, splitPosition.value))
      try {
        cesiumViewer.value?.enableSplitCompare?.(splitCompareEnabled.value, splitPosition.value)
      } catch (_) {
        // ignore
      }
    }

    function _removeSplitDragListeners() {
      window.removeEventListener('pointermove', _onSplitPointerMove)
      window.removeEventListener('pointerup', _onSplitPointerUp)
      window.removeEventListener('pointercancel', _onSplitPointerUp)
    }

    function _recalcSplitBounds() {
      const min = 0.02
      let max = 0.98
      try {
        const el = aiPanelEl.value
        if (el && appState.value === 'analyzing') {
          const rect = el.getBoundingClientRect()
          const panelW = rect?.width || 0
          const w = window.innerWidth || 1
          // Keep the split line out of the right panel area
          const maxX = w - panelW - 10
          max = maxX / w
        }
      } catch (_) {
        // ignore
      }

      // Safety clamp
      const safeMax = Math.min(0.98, Math.max(min + 0.05, max))
      splitMinPos.value = min
      splitMaxPos.value = safeMax
    }

    function _setSplitFromClientX(clientX) {
      const w = window.innerWidth || 1
      const min = splitMinPos.value
      const max = splitMaxPos.value
      const p = Math.min(max, Math.max(min, clientX / w))
      splitPosition.value = p
      try {
        cesiumViewer.value?.setSplitPosition?.(p)
      } catch (_) {
        // ignore
      }
    }

    function onSplitHandleDown(e) {
      if (!splitCompareEnabled.value) return
      draggingSplit.value = true
      _setSplitFromClientX(e.clientX)

      _removeSplitDragListeners()
      window.addEventListener('pointermove', _onSplitPointerMove, { passive: true })
      window.addEventListener('pointerup', _onSplitPointerUp, { passive: true })
      window.addEventListener('pointercancel', _onSplitPointerUp, { passive: true })
    }

    function _onSplitPointerMove(e) {
      if (!draggingSplit.value) return
      _setSplitFromClientX(e.clientX)
    }

    function _onSplitPointerUp() {
      draggingSplit.value = false
      _removeSplitDragListeners()
    }
    
    return {
      cesiumViewer,
      aiPanelEl,
      locations,
      modes,
      missions,
      getChapterCode,
      initialLocation,
      loading,
      viewerReady,
      appState,
      currentMission,
      currentLocationData,
      currentTargetName,
      selectedMissionId,
      selectedLocation,
      selectedMode,
      isCached,
      perfStats,
      zonalStats,
      reportText,
      analysisText,
      commanderBrief,
      insightsText,
      legendHint,
      prefetchState,
      aiLayerVisible,
      holdingCompare,
      splitCompareEnabled,
      splitPosition,
      statusMsg,
      statusType,
      onViewerReady,
      onMapCenterChanged,
      mapCenterText,
      lockMission,
      abortAndOrbit,
      toggleAILayer,
      toggleSplitCompare,
      beginHoldCompare,
      endHoldCompare,
      onSplitHandleDown
    }
  }
}
</script>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.debug-center {
  position: absolute;
  left: 14px;
  bottom: 14px;
  z-index: 1600;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 245, 255, 0.22);
  background: rgba(10, 15, 25, 0.62);
  color: rgba(255, 255, 255, 0.92);
  font-size: 12px;
  letter-spacing: 0.6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  user-select: text;
  pointer-events: none;
}

/* Optional UI polish: hide Cesium default bottom bar/credits area (PoC demo only). */
:deep(.cesium-viewer-bottom) {
  display: none !important;
}

.lobby {
  position: absolute;
  inset: 0;
  z-index: 1000;
  background: radial-gradient(circle at center, rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0.85));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 64px 24px 28px;
}

.lobby-hero {
  pointer-events: none;
  text-align: center;
}

.hero-title {
  font-size: 86px;
  letter-spacing: 10px;
  font-weight: 900;
  color: #ffffff;
  text-shadow: 0 0 30px rgba(0, 245, 255, 0.35);
}

.subtitle {
  margin-top: 10px;
  color: #00f5ff;
  letter-spacing: 4px;
  font-weight: 700;
  font-size: 16px;
}

.lobby-hint {
  margin-top: 14px;
  font-size: 15px;
  letter-spacing: 0.6px;
  color: rgba(255, 255, 255, 0.72);
}

.mission-deck {
  pointer-events: auto;
  margin: 0 auto;
  width: min(1060px, 94vw);
  background: rgba(10, 15, 25, 0.78);
  border: 1px solid rgba(0, 245, 255, 0.22);
  border-radius: 12px;
  padding: 16px 16px 12px;
  backdrop-filter: blur(10px);
}

.deck-title {
  color: rgba(255, 255, 255, 0.92);
  font-weight: 800;
  letter-spacing: 0.4px;
  margin-bottom: 10px;
  font-size: 16px;
}

.mission-card-title {
  font-weight: 900;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
  font-size: 16px;
  line-height: 1.25;
}

.mission-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.mission-empty {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.mission-card {
  padding: 12px 12px 10px;
  background: rgba(0, 245, 255, 0.08);
  border: 1px solid rgba(0, 245, 255, 0.25);
  border-radius: 10px;
  color: #fff;
  cursor: pointer;
  transition: 0.25s;
  text-align: left;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 6px;
  min-height: 128px;
}

.mission-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.mission-card:hover:enabled {
  background: rgba(0, 245, 255, 0.18);
  border-color: rgba(0, 245, 255, 0.45);
  box-shadow: 0 0 24px rgba(0, 245, 255, 0.18);
  transform: translateY(-1px);
}

.mission-card-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 2px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 800;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.92);
}

.tag.secondary {
  color: rgba(0, 245, 255, 0.92);
  border-color: rgba(0, 245, 255, 0.22);
  background: rgba(0, 245, 255, 0.08);
}

.tag.tertiary {
  color: rgba(255, 255, 255, 0.88);
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.04);
}

.tag.formula {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-weight: 800;
  letter-spacing: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mission-card-desc {
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  line-height: 1.5;
  min-height: 54px;
  flex: 1;
}

.mission-card-foot {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.28);
}

.dot.ok {
  background: rgba(0, 255, 120, 0.9);
  box-shadow: 0 0 12px rgba(0, 255, 120, 0.25);
}

.dot.bad {
  background: rgba(255, 80, 80, 0.9);
  box-shadow: 0 0 12px rgba(255, 80, 80, 0.22);
}

.dot.idle {
  background: rgba(255, 255, 255, 0.28);
}

.foot-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.abort-btn {
  position: absolute;
  top: 18px;
  left: 18px;
  z-index: 1400;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(255, 80, 80, 0.35);
  background: rgba(30, 10, 10, 0.72);
  color: #fff;
  font-weight: 900;
  letter-spacing: 0.2px;
  cursor: pointer;
  backdrop-filter: blur(10px);
  box-shadow: 0 0 16px rgba(255, 60, 60, 0.12);
}

.abort-btn:hover:enabled {
  background: rgba(255, 80, 80, 0.18);
  border-color: rgba(255, 120, 120, 0.5);
}

.abort-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: min(520px, 92vw);
  height: 100vh;
  z-index: 1200;
  background: rgba(8, 10, 15, 0.82);
  border-left: 1px solid rgba(0, 245, 255, 0.18);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
}

.ai-header {
  padding: 16px 16px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ai-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.split-compare {
  position: absolute;
  inset: 0;
  z-index: 1300;
  pointer-events: none;
}

.split-line {
  position: absolute;
  top: 0;
  height: 100%;
  width: 2px;
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 0 18px rgba(0, 245, 255, 0.22);
}

.split-handle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 34px;
  height: 60px;
  border-radius: 14px;
  border: 1px solid rgba(0, 245, 255, 0.25);
  background: rgba(10, 15, 25, 0.65);
  backdrop-filter: blur(10px);
  box-shadow: 0 0 16px rgba(0, 245, 255, 0.15);
  pointer-events: auto;
  cursor: ew-resize;
}

.split-handle::before {
  content: '';
  position: absolute;
  inset: 10px 15px;
  border-left: 2px solid rgba(255, 255, 255, 0.28);
  border-right: 2px solid rgba(255, 255, 255, 0.28);
}

.ai-btn {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 245, 255, 0.22);
  background: rgba(0, 245, 255, 0.08);
  color: rgba(255, 255, 255, 0.92);
  font-weight: 900;
  font-size: 11px;
  letter-spacing: 0.2px;
  cursor: pointer;
  backdrop-filter: blur(10px);
  user-select: none;
}

.ai-btn:hover:enabled {
  background: rgba(0, 245, 255, 0.16);
  border-color: rgba(0, 245, 255, 0.38);
}

.ai-btn.secondary {
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
}

.ai-btn.secondary.active {
  border-color: rgba(255, 180, 60, 0.35);
  background: rgba(255, 180, 60, 0.10);
}

.ai-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-title {
  font-weight: 900;
  letter-spacing: 2px;
  color: #fff;
}

.ai-title span {
  color: #00f5ff;
}

.ai-sub {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.ai-sub .k {
  color: rgba(255, 255, 255, 0.55);
  font-weight: 800;
}

.ai-sub .v {
  color: rgba(255, 255, 255, 0.92);
  font-weight: 800;
}

.ai-sub .sep {
  opacity: 0.5;
}

.ai-status {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(255, 255, 255, 0.04);
}

.ai-status .badge {
  font-size: 11px;
  font-weight: 900;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(0, 245, 255, 0.22);
  background: rgba(0, 245, 255, 0.08);
  color: rgba(0, 245, 255, 0.95);
}

.ai-status .msg {
  font-size: 12px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.86);
}

.ai-status.loading {
  border-color: rgba(255, 255, 102, 0.22);
}

.ai-status.success {
  border-color: rgba(0, 255, 120, 0.18);
}

.ai-status.error {
  border-color: rgba(255, 80, 80, 0.22);
}

.ai-body {
  padding: 14px 16px;
  overflow: auto;
}

.commander-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cmd-block {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
}

.cmd-label {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.4px;
  color: rgba(255, 255, 255, 0.62);
  margin-bottom: 8px;
}

.cmd-text {
  font-size: 13px;
  font-weight: 800;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.90);
}

.cmd-legends {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.cmd-legend {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cmd-swatch {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.25) inset;
}

.cmd-legend-label {
  font-size: 12px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.84);
}

.cmd-hint {
  margin-top: 10px;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.5;
  color: rgba(0, 245, 255, 0.80);
  letter-spacing: 0.2px;
}

.cmd-insights {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.88);
  padding: 10px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px dashed rgba(0, 245, 255, 0.14);
  margin: 0;
}

.cmd-details {
  margin-top: 2px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(0, 245, 255, 0.10);
  background: rgba(0, 0, 0, 0.15);
}

.cmd-details > summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
  color: rgba(0, 245, 255, 0.85);
  letter-spacing: 0.4px;
}

.ai-section-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 0.4px;
  font-weight: 900;
  margin-bottom: 10px;
}

.ai-console {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.88);
  padding: 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(0, 245, 255, 0.10);
}

.ai-report {
  margin-top: 16px;
}

.ai-report-box {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.86);
  padding: 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Transitions */
.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.8s ease;
}

.fade-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.fade-up-leave-to {
  opacity: 0;
  transform: scale(1.05);
  filter: blur(6px);
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-40px);
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: 0.15s;
}

.slide-left-enter-from,
.slide-left-leave-to {
  opacity: 0;
  transform: translateX(40px);
}

@media (max-width: 1180px) {
  .mission-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .mission-row {
    grid-template-columns: 1fr;
  }
}
</style>
