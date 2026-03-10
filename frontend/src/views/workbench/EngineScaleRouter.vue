<template>
  <div class="engine-scale-router absolute inset-0 z-0 bg-black">
    <EngineRouter
      v-if="isEarth"
      ref="earthTwin"
      class="absolute inset-0"
      :scenario="scenario"
      :layers="earthLayers"
      @viewer-ready="$emit('viewer-ready', $event)"
    />

    <ThreeTwin
      v-else
      ref="threeTwin"
      class="absolute inset-0"
      :layers="layers"
      @ready="onThreeReady"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useResearchStore } from '../../stores/researchStore.js'
import EngineRouter from './EngineRouter.vue'
import ThreeTwin from './engines/ThreeTwin.vue'

const props = defineProps({
  scenario: { type: Object, default: null },
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['viewer-ready'])

const store = useResearchStore()
const isEarth = computed(() => store.currentScale.value === 'earth')

const earthLayers = computed(() => {
  const allowed = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask', 'ai-imagery', 'ai-vector'])
  return (Array.isArray(props.layers) ? props.layers : []).filter((l) => allowed.has(String(l?.id || '')))
})

const earthTwin = ref(null)
const threeTwin = ref(null)

function onThreeReady() {
  try {
    emit('viewer-ready')
  } catch (_) {
    // ignore
  }
}

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

async function rebuildMicroLattice() {
  try {
    return await threeTwin.value?.rebuildMicroLattice?.()
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
  setSwipeMode,
  setSwipePosition,
  highlightMacroCluster,
  spinMacroCamera,
  rebuildMicroLattice,
})
</script>
