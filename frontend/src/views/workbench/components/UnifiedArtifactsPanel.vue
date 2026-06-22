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
        <div v-if="currentScale === 'earth'" class="swipe-box" aria-label="Swipe Settings">
          <div class="swipe-title">VIEW MODE</div>
          <div class="mode-toggle" role="group" aria-label="View Mode">
            <button
              class="mode-btn"
              type="button"
              :aria-pressed="!swipeEnabledModel"
              :class="{ active: !swipeEnabledModel }"
              @click="swipeEnabledModel = false"
            >
              Overlay
            </button>
            <button
              class="mode-btn"
              type="button"
              :aria-pressed="swipeEnabledModel"
              :class="{ active: swipeEnabledModel }"
              @click="swipeEnabledModel = true"
            >
              Swipe
            </button>
          </div>

          <div v-if="swipeEnabledModel" class="swipe-config" aria-label="Swipe Settings">
            <div class="swipe-hint">Swipe 模式下：左侧保持纯净底图；右侧叠加所有已启用的业务/AI 图层。</div>
          </div>
        </div>
        <LayerTree v-model:layers="layersModel" :current-scale="currentScale" />
      </section>

      <section v-else-if="tab === 'code'" class="panel code-panel" aria-label="Code & Script">
        <div class="code-head">
          <span class="code-title">EDITOR (WGSL/GLSL)</span>
          <div class="code-actions">
            <button class="run-btn" type="button" @click="onRunCode">⟳ HOT RELOAD</button>
          </div>
        </div>
        <div class="code-editor">
          <MonacoLazyEditor v-model="codeModel" language="wgsl" />
        </div>
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
import { computed, ref, watch } from 'vue'
import LayerTree from './LayerTree.vue'
import MonacoLazyEditor from '../../../components/MonacoLazyEditor.vue'

const props = defineProps({
  layers: { type: Array, default: () => [] },
  currentScale: { type: String, default: 'earth' },
  code: { type: String, default: '' },
  reportText: { type: String, default: '' },
  charts: { type: Array, default: () => [] },
  swipeEnabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:layers', 'update:code', 'update:swipeEnabled', 'run-code'])

const tab = ref('layers')

function setTab(nextTab) {
  const t = String(nextTab || '').trim().toLowerCase()
  if (t === 'layers' || t === 'code' || t === 'charts' || t === 'reports') tab.value = t
}

defineExpose({ setTab })

// UX: when WebGPU tool calls emit diagnostics, surface them immediately.
watch(
  () => String(props.reportText || ''),
  (v) => {
    const s = String(v || '').trim()
    if (!s) return
    if (s.includes('[WebGPU]')) tab.value = 'reports'
  }
)

const swipeEnabledModel = computed({
  get() {
    return !!props.swipeEnabled
  },
  set(v) {
    emit('update:swipeEnabled', !!v)
  },
})

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

function onRunCode() {
  try {
    emit('run-code', String(codeModel.value || ''))
  } catch (_) {
    // ignore
  }
}

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

.code-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  /* CODE wants an IDE-like fill; avoid nested scrollbars. */
  padding: 0;
}

.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 10px 0 10px;
}

.code-title {
  font-size: 10px;
  opacity: 0.72;
  letter-spacing: 0.15em;
  font-weight: 900;
}

.code-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.run-btn {
  background: rgba(0, 240, 255, 0.12);
  border: 1px solid rgba(0, 240, 255, 0.30);
  color: rgba(0, 240, 255, 0.95);
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 900;
  cursor: pointer;
  transition: background 120ms ease;
}

.run-btn:hover {
  background: rgba(0, 240, 255, 0.22);
}

.code-editor {
  flex: 1;
  min-height: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.10);
  margin: 0 10px 10px 10px;
}

/* Let Monaco shrink/grow with the panel without forcing parent scroll. */
.code-editor :deep(.monaco-shell) {
  height: 100%;
  min-height: 0;
}

.code-editor :deep(.host),
.code-editor :deep(.fallback) {
  min-height: 0;
}

.swipe-box {
  border-radius: 14px;
  padding: 10px;
  margin-bottom: 10px;
  background: rgba(10, 15, 26, 0.20);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.swipe-title {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  font-weight: 900;
  opacity: 0.82;
  margin-bottom: 8px;
}

.mode-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 4px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.18);
  margin-bottom: 10px;
}

.mode-btn {
  border: 1px solid transparent;
  background: transparent;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
  padding: 7px 10px;
  border-radius: 12px;
  cursor: pointer;
  letter-spacing: 0.02em;
}

.mode-btn.active {
  background: rgba(0, 240, 255, 0.14);
  border-color: rgba(0, 240, 255, 0.26);
  color: rgba(0, 240, 255, 0.95);
  text-shadow: 0 0 18px rgba(0, 240, 255, 0.20);
}

.swipe-config {
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.swipe-subtitle {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  font-weight: 900;
  opacity: 0.82;
  margin: 6px 0 8px;
}

.swipe-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.swipe-field {
  display: grid;
  gap: 6px;
}

.swipe-k {
  font-size: 11px;
  opacity: 0.78;
}

.swipe-sel {
  width: 100%;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.22);
  color: rgba(255, 255, 255, 0.86);
  padding: 8px 10px;
  font-size: 12px;
  outline: none;
}

.swipe-hint {
  margin-top: 8px;
  font-size: 11px;
  opacity: 0.66;
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
