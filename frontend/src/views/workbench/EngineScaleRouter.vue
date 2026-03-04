<template>
  <div class="engine-scale-router absolute inset-0 z-0 bg-black">
    <EngineRouter
      v-if="isEarth"
      ref="earthTwin"
      class="absolute inset-0"
      :scenario="scenario"
      :layers="layers"
      @viewer-ready="$emit('viewer-ready', $event)"
    />

    <ThreeTwin v-else class="absolute inset-0" @ready="onThreeReady" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useResearchStore } from '../../stores/researchStore.js'
import EngineRouter from './EngineRouter.vue'
import ThreeTwin from './engines/ThreeTwin.vue'

defineProps({
  scenario: { type: Object, default: null },
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['viewer-ready'])

const store = useResearchStore()
const isEarth = computed(() => store.currentScale.value === 'earth')

const earthTwin = ref(null)

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

defineExpose({
  flyToScenario,
})
</script>
