<template>
  <div class="engine-router" aria-label="Engine Router">
    <!-- MVP: always mount Cesium Twin. Three.js modes are Phase 2. -->
    <CesiumViewer
      ref="cesiumViewer"
      :initial-location="initialLocation"
      @viewer-ready="onViewerReady"
    />
  </div>
</template>

<script setup>
import * as Cesium from 'cesium'
import { computed, ref, watch } from 'vue'
import CesiumViewer from '../../components/CesiumViewer.vue'

const props = defineProps({
  scenario: { type: Object, default: null },
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['viewer-ready'])

const cesiumViewer = ref(null)
const cesiumViewerInstance = ref(null)
const overlayHandles = ref(new Map())

const initialLocation = computed(() => props.scenario?.camera || undefined)

function flyToScenario() {
  const cam = props.scenario?.camera
  if (!cam) return
  try {
    const d = Number(cam.duration_s)
    const duration = Number.isFinite(d) && d > 0 ? d : 3.8
    cesiumViewer.value?.flyTo?.(cam, duration)
  } catch (_) {
    // ignore
  }
}

function onViewerReady(viewer) {
  cesiumViewerInstance.value = viewer || null
  emit('viewer-ready', viewer)
  try {
    ensureOverlays()
    applyLayers(props.layers)
  } catch (_) {
    // ignore
  }
}

function _anchorRect() {
  const lon = Number(props.scenario?.camera?.lon)
  const lat = Number(props.scenario?.camera?.lat)
  const ok = Number.isFinite(lon) && Number.isFinite(lat)
  const x = ok ? lon : 115.98
  const y = ok ? lat : 39.05
  const dlon = 0.55
  const dlat = 0.35
  return Cesium.Rectangle.fromDegrees(x - dlon, y - dlat, x + dlon, y + dlat)
}

function ensureOverlays() {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return
  const map = overlayHandles.value
  const rect = _anchorRect()

  function _ensure(id, build) {
    if (map.has(id)) return
    try {
      map.set(id, build())
    } catch (_) {
      // ignore
    }
  }

  _ensure('boundaries', () => {
    return viewer.entities.add({
      name: 'Vector Boundaries (stub)',
      show: true,
      rectangle: {
        coordinates: rect,
        material: Cesium.Color.TRANSPARENT,
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(0.85),
        outlineWidth: 2,
        height: 0,
      },
    })
  })

  _ensure('gee-heatmap', () => {
    return viewer.entities.add({
      name: 'GEE Heatmap (stub)',
      show: true,
      rectangle: {
        coordinates: rect,
        material: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(0.18),
        outline: false,
      },
    })
  })

  _ensure('anomaly-mask', () => {
    return viewer.entities.add({
      name: 'Anomaly Mask (stub)',
      show: false,
      rectangle: {
        coordinates: rect,
        material: Cesium.Color.fromCssColorString('#FF4D6D').withAlpha(0.14),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#FF4D6D').withAlpha(0.55),
      },
    })
  })
}

function applyLayers(layers) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return
  ensureOverlays()

  const arr = Array.isArray(layers) ? layers : []
  const map = overlayHandles.value

  for (const l of arr) {
    const id = String(l?.id || '').trim()
    if (!id) continue
    const h = map.get(id)
    if (!h) continue
    try {
      h.show = !!l.enabled
    } catch (_) {
      // ignore
    }
  }

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
}

watch(
  () => props.scenario?.id,
  () => flyToScenario()
)

watch(
  () => props.layers,
  (v) => {
    try {
      applyLayers(v)
    } catch (_) {
      // ignore
    }
  },
  { deep: true }
)

defineExpose({
  flyToScenario,
  applyLayers,
  cesiumViewer,
  cesiumViewerInstance,
})
</script>

<style scoped>
.engine-router {
  position: absolute;
  inset: 0;
}

.engine-router :deep(.cesium-viewer-container) {
  width: 100%;
  height: 100%;
}
</style>
