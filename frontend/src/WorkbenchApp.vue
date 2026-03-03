<template>
  <div class="wb" data-testid="workbench">
    <!-- Z-index: 0 — full-screen twin engine (Cesium owns the viewport) -->
    <div class="wb-engine" aria-label="Cesium Twin">
      <CesiumViewer
        ref="cesiumViewer"
        :initial-location="scenario?.camera || undefined"
        @viewer-ready="onViewerReady"
      />
      <div v-if="!viewerReady" class="wb-engine-status">正在唤醒 Cesium…</div>
    </div>

    <!-- Z-index: 10 — holographic HUD (mouse passes through empty areas) -->
    <div class="wb-ui-layer" aria-label="Workbench HUD">
      <header class="wb-panel wb-top">
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
          <a class="btn secondary" href="/">Back</a>
        </div>
      </header>

      <section class="wb-panel wb-left" aria-label="Agent Flow">
        <div class="pane-title">021 MODEL FLOW</div>
        <pre class="pane-pre">{{ agentText }}</pre>

        <div class="pane-row">
          <button class="btn" type="button" @click="runStub">EXECUTE ON TWIN</button>
          <button class="btn secondary" type="button" @click="reset">Reset</button>
        </div>
      </section>

      <section class="wb-panel wb-right" aria-label="Code Editor">
        <div class="pane-title">CODE</div>
        <div class="editor-shell">
          <MonacoLazyEditor v-model="code" language="python" />
        </div>
      </section>
    </div>
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
  position: relative;
  width: 100vw;
  height: 100vh;
  background: #000;
  color: #eef2ff;
  overflow: hidden;
}

.wb-engine {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.wb-engine :deep(.cesium-viewer-container) {
  width: 100%;
  height: 100%;
}

.wb-engine-status {
  position: absolute;
  left: 18px;
  bottom: 18px;
  z-index: 1;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.30);
  border: 1px solid rgba(255, 255, 255, 0.10);
  font-size: 12px;
  backdrop-filter: blur(12px);
}

.wb-ui-layer {
  position: fixed;
  inset: 0;
  z-index: 10;
  pointer-events: none;
}

.wb-panel {
  pointer-events: auto;
  background: rgba(10, 15, 26, 0.40);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 16px;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.55);
}

.wb-top {
  position: absolute;
  top: 18px;
  left: 18px;
  right: 18px;
  height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
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

.wb-left,
.wb-right {
  position: absolute;
  top: 96px;
  bottom: 18px;
  width: min(420px, 34vw);
  padding: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wb-left {
  left: 18px;
}

.wb-right {
  right: 18px;
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

.editor-shell {
  flex: 1;
  min-height: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.28);
}

@media (max-width: 980px) {
  .wb-ui-layer {
    position: relative;
    inset: auto;
    padding: 12px;
    pointer-events: auto;
  }

  .wb-engine {
    position: relative;
    height: 52vh;
  }

  .wb-top {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    margin-bottom: 12px;
  }

  .wb-left,
  .wb-right {
    position: relative;
    top: auto;
    bottom: auto;
    left: auto;
    right: auto;
    width: 100%;
    height: 320px;
    margin-bottom: 12px;
  }
}
</style>
