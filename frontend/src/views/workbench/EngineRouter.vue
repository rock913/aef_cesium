<template>
  <div class="engine-router" aria-label="Engine Router">
    <!-- MVP: always mount Cesium Twin. Three.js modes are Phase 2. -->
    <CesiumViewer
      ref="cesiumViewer"
      :initial-location="initialLocation"
      @viewer-ready="() => emit('viewer-ready')"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import CesiumViewer from '../../components/CesiumViewer.vue'

const props = defineProps({
  scenario: { type: Object, default: null },
})

const emit = defineEmits(['viewer-ready'])

const cesiumViewer = ref(null)

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

watch(
  () => props.scenario?.id,
  () => flyToScenario()
)

defineExpose({
  flyToScenario,
  cesiumViewer,
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
