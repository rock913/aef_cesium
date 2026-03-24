<template>
  <div class="engine-scale-router absolute inset-0 z-0 bg-black">
    <div ref="earthWrap" class="engine-wrap absolute inset-0">
      <EngineRouter
        ref="earthTwin"
        class="absolute inset-0"
        :scenario="scenario"
        :layers="earthLayers"
        @viewer-ready="onCesiumViewerReady"
      />
    </div>

    <div ref="threeWrap" class="engine-wrap absolute inset-0">
      <ThreeTwin ref="threeTwin" class="absolute inset-0" :layers="layers" @ready="onThreeReady" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { gsap } from 'gsap'
import { useResearchStore } from '../../stores/researchStore.js'
import EngineRouter from './EngineRouter.vue'
import ThreeTwin from './engines/ThreeTwin.vue'
import { syncCesiumToThreeCamera } from '../../utils/astronomy/engineHandover.js'

const props = defineProps({
  scenario: { type: Object, default: null },
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['viewer-ready'])

const store = useResearchStore()
const currentScale = computed(() => store.currentScale.value)
const isEarth = computed(() => currentScale.value === 'earth')

const earthLayers = computed(() => {
  const allowed = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask', 'ai-imagery', 'ai-vector'])
  return (Array.isArray(props.layers) ? props.layers : []).filter((l) => allowed.has(String(l?.id || '')))
})

const earthTwin = ref(null)
const threeTwin = ref(null)

const earthWrap = ref(null)
const threeWrap = ref(null)

const cesiumViewerRef = ref(null)

// P0: Earth→Sky one-shot handover (camera height threshold triggers macro scale).
const HANDOVER_HEIGHT_KM = (() => {
  const raw = String(import.meta.env.VITE_EARTH_TO_SKY_HANDOVER_HEIGHT_KM || '').trim()
  const km = Number(raw)
  return Number.isFinite(km) && km > 0 ? km : 20000
})()
const HANDOVER_HEIGHT_M = HANDOVER_HEIGHT_KM * 1000

let _autoHandoverUnsub = null
let _autoHandoverTriggered = false
let _autoHandoverPrevH = null
let _autoHandoverZoomOutScore = 0

function applyEngineVisibility({ earthActive, instant = false } = {}) {
  if (!earthWrap.value || !threeWrap.value) return

  const duration = instant ? 0 : 0.65
  const ease = 'power2.out'

  earthWrap.value.style.pointerEvents = earthActive ? 'auto' : 'none'
  threeWrap.value.style.pointerEvents = earthActive ? 'none' : 'auto'

  gsap.to(earthWrap.value, { opacity: earthActive ? 1 : 0, duration, ease })
  gsap.to(threeWrap.value, { opacity: earthActive ? 0 : 1, duration, ease })
}

function tryHandoverEarthToThree() {
  try {
    const viewer =
      cesiumViewerRef.value || earthTwin.value?.cesiumViewerInstance || earthTwin.value?.cesiumViewer || null
    const cesiumCamera = viewer?.camera
    const threeCamera = threeTwin.value?.getCamera?.() || null
    if (!cesiumCamera || !threeCamera) return
    syncCesiumToThreeCamera(cesiumCamera, threeCamera)
  } catch (_) {
    // ignore
  }
}

function onCesiumViewerReady(viewer) {
  try {
    cesiumViewerRef.value = viewer
  } catch (_) {
    // ignore
  }

  // Install camera-height driven auto-handover.
  try {
    _installEarthToSkyAutoHandover(viewer)
  } catch (_) {
    // ignore
  }

  try {
    emit('viewer-ready', viewer)
  } catch (_) {
    // ignore
  }
}

function _installEarthToSkyAutoHandover(viewer) {
  if (!viewer?.camera?.changed?.addEventListener) return

  try {
    _autoHandoverUnsub?.()
  } catch (_) {
    // ignore
  }
  _autoHandoverUnsub = null

  let rafPending = false
  const onChanged = () => {
    if (rafPending) return
    rafPending = true
    try {
      requestAnimationFrame(() => {
        rafPending = false
        const h = Number(viewer.camera?.positionCartographic?.height)
        if (!Number.isFinite(h)) return

        if (_autoHandoverPrevH === null) _autoHandoverPrevH = h
        const dh = h - _autoHandoverPrevH
        _autoHandoverPrevH = h

        // Detect zoom-out intent (height increasing across several samples).
        if (dh > 2500) _autoHandoverZoomOutScore = Math.min(6, _autoHandoverZoomOutScore + 1)
        else _autoHandoverZoomOutScore = Math.max(0, _autoHandoverZoomOutScore - 1)

        // Allow re-trigger if user comes back down.
        if (_autoHandoverTriggered && h < HANDOVER_HEIGHT_M * 0.7) {
          _autoHandoverTriggered = false
          _autoHandoverZoomOutScore = 0
        }

        if (_autoHandoverTriggered) return
        if (store.currentScale.value !== 'earth') return
        if (h < HANDOVER_HEIGHT_M) return
        if (_autoHandoverZoomOutScore < 3) return

        _autoHandoverTriggered = true
        try {
          tryHandoverEarthToThree()
        } catch (_) {
          // ignore
        }
        try {
          store.setScale('macro')
        } catch (_) {
          // ignore
        }
      })
    } catch (_) {
      rafPending = false
    }
  }

  viewer.camera.changed.addEventListener(onChanged)
  _autoHandoverUnsub = () => {
    try {
      viewer.camera.changed.removeEventListener(onChanged)
    } catch (_) {
      // ignore
    }
  }
}

function onThreeReady() {
  try {
    emit('viewer-ready')
  } catch (_) {
    // ignore
  }
}

watch(
  () => currentScale.value,
  async (next, prev) => {
    await nextTick()
    const earthActive = next === 'earth'
    if (prev === 'earth' && next !== 'earth') {
      tryHandoverEarthToThree()
    }
    applyEngineVisibility({ earthActive })
  },
  { immediate: true }
)

onMounted(() => {
  try {
    applyEngineVisibility({ earthActive: isEarth.value, instant: true })
  } catch (_) {
    // ignore
  }
})

onBeforeUnmount(() => {
  try {
    _autoHandoverUnsub?.()
  } catch (_) {
    // ignore
  }
  _autoHandoverUnsub = null
})

function flyToScenario() {
  try {
    earthTwin.value?.flyToScenario?.()
  } catch (_) {
    // ignore
  }
}

function startGlobalStandby() {
  try {
    earthTwin.value?.startGlobalStandby?.()
  } catch (_) {
    // ignore
  }
}

function stopGlobalStandby() {
  try {
    earthTwin.value?.stopGlobalStandby?.()
  } catch (_) {
    // ignore
  }
}

function flyToLocation(location, duration) {
  try {
    earthTwin.value?.flyToLocation?.(location, duration)
  } catch (_) {
    // ignore
  }
}

async function enable3DTerrain(opts) {
  try {
    return await earthTwin.value?.enable3DTerrain?.(opts)
  } catch (_) {
    // ignore
  }
}

async function addCesium3DTiles(opts) {
  try {
    return await earthTwin.value?.addCesium3DTiles?.(opts)
  } catch (_) {
    // ignore
  }
}

function enableSubsurfaceMode(opts) {
  try {
    return earthTwin.value?.enableSubsurfaceMode?.(opts)
  } catch (_) {
    // ignore
  }
}

function disableSubsurfaceMode() {
  try {
    return earthTwin.value?.disableSubsurfaceMode?.()
  } catch (_) {
    // ignore
  }
}

async function addSubsurfaceModel(opts) {
  try {
    return await earthTwin.value?.addSubsurfaceModel?.(opts)
  } catch (_) {
    // ignore
  }
}

async function addWaterPolygon(opts) {
  try {
    return await earthTwin.value?.addWaterPolygon?.(opts)
  } catch (_) {
    // ignore
  }
}

async function executeDynamicWgsl(opts) {
  try {
    return await earthTwin.value?.executeDynamicWgsl?.(opts)
  } catch (_) {
    // ignore
  }
}

function destroyWebGpuSandbox() {
  try {
    return earthTwin.value?.destroyWebGpuSandbox?.()
  } catch (_) {
    // ignore
  }
}

async function applyCustomShader(opts) {
  try {
    return await earthTwin.value?.applyCustomShader?.(opts)
  } catch (_) {
    // ignore
  }
}

function setSceneMode(mode) {
  try {
    return earthTwin.value?.setSceneMode?.(mode)
  } catch (_) {
    // ignore
  }
}

async function playCzmlAnimation(opts) {
  try {
    return await earthTwin.value?.playCzmlAnimation?.(opts)
  } catch (_) {
    // ignore
  }
}

function setGlobeTransparency(alpha) {
  try {
    return earthTwin.value?.setGlobeTransparency?.(alpha)
  } catch (_) {
    // ignore
  }
}

async function addExtrudedPolygons(opts) {
  try {
    return await earthTwin.value?.addExtrudedPolygons?.(opts)
  } catch (_) {
    // ignore
  }
}

async function renderBivariateGridOverlay(opts) {
  try {
    return await earthTwin.value?.renderBivariateGridOverlay?.(opts)
  } catch (_) {
    // ignore
  }
}

function setSwipeMode(opts) {
  try {
    return earthTwin.value?.setSwipeMode?.(opts)
  } catch (_) {
    // ignore
  }
}

function setSwipePosition(pos) {
  try {
    return earthTwin.value?.setSwipePosition?.(pos)
  } catch (_) {
    // ignore
  }
}

async function highlightMacroCluster() {
  try {
    return await threeTwin.value?.highlightMacroCluster?.()
  } catch (_) {
    // ignore
  }
}

async function spinMacroCamera(opts) {
  try {
    return await threeTwin.value?.spinMacroCamera?.(opts)
  } catch (_) {
    // ignore
  }
}

async function rebuildMicroLattice(opts) {
  try {
    return await threeTwin.value?.rebuildMicroLattice?.(opts)
  } catch (_) {
    // ignore
  }
}

defineExpose({
  flyToScenario,
  startGlobalStandby,
  stopGlobalStandby,
  flyToLocation,
  enable3DTerrain,
  addCesium3DTiles,
  enableSubsurfaceMode,
  disableSubsurfaceMode,
  addSubsurfaceModel,
  addWaterPolygon,
  executeDynamicWgsl,
  destroyWebGpuSandbox,
  applyCustomShader,
  setSceneMode,
  playCzmlAnimation,
  setGlobeTransparency,
  addExtrudedPolygons,
  renderBivariateGridOverlay,
  setSwipeMode,
  setSwipePosition,
  highlightMacroCluster,
  spinMacroCamera,
  rebuildMicroLattice,
})
</script>

<style scoped>
.engine-wrap {
  opacity: 0;
}
</style>
