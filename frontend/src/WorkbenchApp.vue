<template>
  <div class="wb" data-testid="workbench">
    <header class="wb-top">
      <div class="wb-brand">
        <div class="k">Zero2x</div>
        <div class="t">AI‑Native Workbench</div>
        <div class="wb-context" data-testid="workbench-context">
          CONTEXT: <span class="v">{{ scenario?.id || '—' }}</span>
          <span class="sep">///</span>
          <span class="v">{{ scenario?.targetName || '—' }}</span>
        </div>
      </div>

      <div class="wb-actions">
        <a class="btn secondary" href="/">Back to Landing</a>
        <a class="btn secondary" href="/demo">Open Demo</a>
      </div>
    </header>

    <main class="wb-grid">
      <section class="pane">
        <div class="pane-title">Agent Flow</div>
        <pre class="pane-pre">{{ agentText }}</pre>

        <div class="pane-row">
          <button class="btn" type="button" @click="runStub">Run (Stub)</button>
          <button class="btn secondary" type="button" @click="reset">Reset</button>
        </div>
      </section>

      <section class="pane">
        <MonacoLazyEditor v-model="code" language="python" />
      </section>

      <section class="pane">
        <div class="pane-title">Cesium Twin</div>
        <div class="preview cesium-preview">
          <CesiumViewer
            ref="cesiumViewer"
            :initial-location="scenario?.camera || undefined"
            @viewer-ready="onViewerReady"
          />
          <div v-if="!viewerReady" class="preview-sub">正在唤醒 Cesium…</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CesiumViewer from './components/CesiumViewer.vue'
import MonacoLazyEditor from './components/MonacoLazyEditor.vue'
import { getDefaultScenario021, getScenario021ById, parseWorkbenchContextFromSearch } from './utils/scenarios021.js'

const cesiumViewer = ref(null)
const viewerReady = ref(false)

const contextId = ref('poyang')
const scenario = computed(() => getScenario021ById(contextId.value) || getDefaultScenario021())

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

function reset() {
  agentText.value = 'System ready. Press Run to simulate an agent flow…'
}

function _flyToScenario() {
  const sc = scenario.value
  const cam = sc?.camera
  if (!cam) return
  try {
    const d = Number(cam.duration_s)
    const duration = Number.isFinite(d) && d > 0 ? d : 3.8
    cesiumViewer.value?.flyTo?.(cam, duration)
  } catch (_) {
    // ignore
  }
}

function onViewerReady() {
  viewerReady.value = true
  _flyToScenario()
}

watch(
  () => scenario.value?.id,
  () => {
    code.value = buildCodeStub(scenario.value)
    if (viewerReady.value) _flyToScenario()
  }
)

onMounted(() => {
  try {
    document.body.style.overflow = 'hidden'
  } catch (_) {
    // ignore
  }

  try {
    const ctxFromUrl = parseWorkbenchContextFromSearch(window.location.search)
    const ctxFromStorage = window.sessionStorage?.getItem?.('z2x:lastContext') || ''
    contextId.value = String(ctxFromUrl || ctxFromStorage || 'poyang').trim().toLowerCase() || 'poyang'

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
})
</script>

<style scoped>
.wb {
  width: 100vw;
  height: 100vh;
  background: radial-gradient(1200px 800px at 50% 20%, rgba(120, 160, 255, 0.14), rgba(0, 0, 0, 0.25)),
    linear-gradient(180deg, #05070f, #000);
  color: #eef2ff;
  overflow: hidden;
}

.wb-top {
  height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 15, 25, 0.62);
  backdrop-filter: blur(12px);
}

.wb-brand .k {
  font-size: 12px;
  opacity: 0.78;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.wb-brand .t {
  font-weight: 900;
  letter-spacing: 0.4px;
}

.wb-context {
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.78;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.wb-context .v {
  opacity: 0.92;
  letter-spacing: 0.02em;
  text-transform: none;
}

.wb-context .sep {
  margin: 0 8px;
  opacity: 0.42;
}

.wb-actions {
  display: flex;
  gap: 10px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 12px;
  border-radius: 12px;
  background: rgba(120, 160, 255, 0.18);
  border: 1px solid rgba(120, 160, 255, 0.35);
  color: #eef2ff;
  text-decoration: none;
  cursor: pointer;
}

.btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.16);
}

.wb-grid {
  height: calc(100vh - 62px);
  display: grid;
  grid-template-columns: 1.1fr 1.4fr 1.1fr;
  gap: 12px;
  padding: 12px;
}

@media (max-width: 980px) {
  .wb {
    height: auto;
    overflow: auto;
  }

  .wb-top {
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .wb-grid {
    height: auto;
    grid-template-columns: 1fr;
  }

  .pane {
    min-height: 260px;
  }
}

.pane {
  min-width: 0;
  border-radius: 18px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pane-title {
  font-size: 12px;
  opacity: 0.75;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 900;
}

.pane-pre {
  flex: 1;
  white-space: pre-wrap;
  overflow: auto;
  padding: 10px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.pane-row {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.preview {
  padding: 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 120px;
}

.cesium-preview {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 260px;
}

.cesium-preview :deep(.cesium-viewer-container) {
  flex: 1;
}

.preview-sub {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.72;
}

@media (max-width: 980px) {
  .wb-grid {
    grid-template-columns: 1fr;
    grid-auto-rows: minmax(220px, auto);
  }
  .wb {
    height: auto;
  }
}
</style>
