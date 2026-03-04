<template>
  <div class="artifacts" aria-label="Unified Artifacts">
    <div class="artifacts-head">
      <div class="title">UNIFIED ARTIFACTS</div>
      <div class="tabs" role="tablist" aria-label="Artifacts Tabs">
        <button class="tab" type="button" role="tab" :aria-selected="tab === 'layers'" @click="tab = 'layers'">
          LAYER &amp; DATA
        </button>
        <button class="tab" type="button" role="tab" :aria-selected="tab === 'code'" @click="tab = 'code'">
          CODE &amp; SCRIPT
        </button>
        <button class="tab" type="button" role="tab" :aria-selected="tab === 'charts'" @click="tab = 'charts'">
          CHARTS &amp; STATS
        </button>
        <button class="tab" type="button" role="tab" :aria-selected="tab === 'reports'" @click="tab = 'reports'">
          REPORTS
        </button>
      </div>
    </div>

    <div class="artifacts-body" data-testid="artifacts-body">
      <section v-if="tab === 'layers'" class="panel" aria-label="Layer & Data">
        <LayerTree v-model:layers="layersModel" :current-scale="currentScale" />
      </section>

      <section v-else-if="tab === 'code'" class="panel" aria-label="Code & Script">
        <MonacoLazyEditor v-model="codeModel" language="python" />
      </section>

      <section v-else-if="tab === 'charts'" class="panel" aria-label="Charts & Stats">
        <div v-if="charts && charts.length" class="charts-list" aria-label="Charts List">
          <div v-for="c in charts" :key="c.id" class="chart-item">
            <div class="chart-title">{{ c.title || c.kind || 'Chart' }}</div>
            <pre class="chart-pre">{{ stringify(c.data) }}</pre>
          </div>
        </div>
        <div v-else class="placeholder">No charts yet. Run a Copilot prompt that emits show_chart.</div>
      </section>

      <section v-else class="panel" aria-label="Reports">
        <pre class="report-pre">{{ reportText || 'No report yet. Run a Copilot prompt to generate one.' }}</pre>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import LayerTree from './LayerTree.vue'
import MonacoLazyEditor from '../../../components/MonacoLazyEditor.vue'

const props = defineProps({
  layers: { type: Array, default: () => [] },
  currentScale: { type: String, default: 'earth' },
  code: { type: String, default: '' },
  reportText: { type: String, default: '' },
  charts: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:layers', 'update:code'])

const tab = ref('layers')

const layersModel = computed({
  get() {
    return props.layers
  },
  set(v) {
    emit('update:layers', Array.isArray(v) ? v : [])
  },
})

const codeModel = computed({
  get() {
    return props.code
  },
  set(v) {
    emit('update:code', String(v ?? ''))
  },
})

function stringify(v) {
  try {
    return JSON.stringify(v, null, 2)
  } catch (_) {
    return String(v)
  }
}
</script>

<style scoped>
.artifacts {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.artifacts-head {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.title {
  font-size: 11px;
  opacity: 0.78;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 900;
}

.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.tab {
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.78);
  cursor: pointer;
  font-size: 12px;
}

.tab[aria-selected='true'] {
  border-color: rgba(0, 240, 255, 0.32);
  background: rgba(0, 240, 255, 0.10);
  color: rgba(0, 240, 255, 0.95);
}

.artifacts-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
}

.panel {
  height: 100%;
  padding: 10px;
  overflow: auto;
}

.placeholder {
  padding: 12px;
  opacity: 0.75;
  font-size: 12px;
}

.charts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-item {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.18);
  padding: 10px;
}

.chart-title {
  font-size: 12px;
  font-weight: 900;
  opacity: 0.85;
  margin-bottom: 8px;
}

.chart-pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 11px;
  line-height: 1.45;
  opacity: 0.9;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.report-pre {
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
</style>
