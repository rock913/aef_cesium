<template>
  <div class="wb" data-testid="workbench">
    <div class="ide" aria-label="Zero2x Spatial IDE">
      <header class="ide-top" aria-label="Workbench Top Bar">
        <div class="ide-title">ZERO2X 021 WORKBENCH</div>
        <div class="ide-top-actions">
          <button class="top-link" type="button" @click="toggleImmersive">{{ isImmersive ? '退出沉浸' : '沉浸模式 (F11)' }}</button>
        </div>
      </header>

      <div class="ide-body">
        <aside v-show="isAgentOpen" class="ide-aside left" aria-label="Agent Sidebar">
          <AgentPanel :text="agentText" @execute="runStub" @reset="reset" />
        </aside>

        <main class="ide-main" aria-label="Main Canvas">
          <div v-show="!isImmersive" class="ide-tabs" aria-label="Tabs">
            <div class="tab active">Spatial Canvas</div>
            <div class="tab ghost">Dataframe.csv</div>
          </div>

          <div class="ide-canvas" aria-label="Canvas">
            <EngineRouter ref="engineRouter" :scenario="scenario" @viewer-ready="onViewerReady" />
            <div v-if="!viewerReady" class="engine-status">正在唤醒 Cesium…</div>

            <TimelineHUD v-show="!isImmersive" class="timeline-hud" @execute="runStub" />
          </div>
        </main>

        <aside v-show="isEditorOpen" class="ide-aside right" aria-label="Editor Sidebar">
          <EditorPanel>
            <MonacoLazyEditor v-model="code" language="python" />
          </EditorPanel>
        </aside>
      </div>

      <div v-if="isOmniOpen" class="omnibox-layer" aria-label="OmniCommand Layer" @pointerdown.self="closeOmni">
        <OmniCommand
          :open="isOmniOpen"
          v-model="omniText"
          :context-label="scenario?.id || ''"
          @submit="submitOmni"
          @close="closeOmni"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MonacoLazyEditor from './components/MonacoLazyEditor.vue'
import { getDefaultScenario021, getScenario021ById, parseWorkbenchContextFromSearch } from './utils/scenarios021.js'
import EngineRouter from './views/workbench/EngineRouter.vue'
import AgentPanel from './views/workbench/components/AgentPanel.vue'
import EditorPanel from './views/workbench/components/EditorPanel.vue'
import TimelineHUD from './views/workbench/components/TimelineHUD.vue'
import OmniCommand from './views/workbench/components/OmniCommand.vue'

const engineRouter = ref(null)
const viewerReady = ref(false)

const isAgentOpen = ref(true)
const isEditorOpen = ref(true)
const isImmersive = ref(false)

const isOmniOpen = ref(false)
const omniText = ref('')

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
  try {
    engineRouter.value?.flyToScenario?.()
  } catch (_) { }
}

function onViewerReady() {
  viewerReady.value = true
  _flyToScenario()
}

function toggleImmersive() {
  isImmersive.value = !isImmersive.value
  if (isImmersive.value) {
    isAgentOpen.value = false
    isEditorOpen.value = false
  } else {
    isAgentOpen.value = true
    isEditorOpen.value = true
  }
}

function openOmni() {
  isOmniOpen.value = true
}

function closeOmni() {
  isOmniOpen.value = false
}

function submitOmni() {
  // MVP: treat OmniCommand input as the lastIntent and replay the demo plan.
  try {
    lastIntent.value = String(omniText.value || '').trim()
    window.sessionStorage?.setItem?.('z2x:lastIntent', lastIntent.value)
  } catch (_) { }
  closeOmni()
  runStub()
}

function onKeydown(e) {
  if (!e) return
  const k = String(e.key || '').toLowerCase()
  if (k === 'f11') {
    e.preventDefault()
    toggleImmersive()
    return
  }
  if ((e.metaKey || e.ctrlKey) && k === 'k') {
    e.preventDefault()
    openOmni()
    return
  }
  if (k === 'escape' && isOmniOpen.value) {
    closeOmni()
  }
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

  window.addEventListener('keydown', onKeydown)

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

  try {
    window.removeEventListener('keydown', onKeydown)
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

.ide {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: radial-gradient(1200px 800px at 50% 20%, rgba(120, 160, 255, 0.10), rgba(0, 0, 0, 0.25)),
    linear-gradient(180deg, #05070f, #000);
}

.ide-top {
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(5, 8, 16, 0.86);
}

.ide-title {
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  letter-spacing: 0.18em;
  color: rgba(0, 240, 255, 0.95);
  font-weight: 900;
}

.ide-top-actions {
  display: flex;
  gap: 10px;
}

.top-link {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  cursor: pointer;
}

.top-link:hover {
  color: rgba(255, 255, 255, 0.95);
}

.ide-body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.ide-aside {
  width: 360px;
  flex-shrink: 0;
  padding: 12px;
  background: rgba(10, 15, 26, 0.92);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.ide-aside.right {
  width: 420px;
  border-right: none;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.ide-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #000;
}

.ide-tabs {
  height: 32px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(5, 8, 16, 0.86);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.tab {
  padding: 6px 12px;
  font-size: 12px;
  border-top: 2px solid transparent;
  opacity: 0.72;
}

.tab.active {
  opacity: 0.95;
  border-top-color: rgba(0, 240, 255, 0.95);
  background: rgba(0, 0, 0, 0.55);
}

.tab.ghost {
  opacity: 0.45;
}

.ide-canvas {
  position: relative;
  flex: 1;
  min-height: 0;
}

.engine-status {
  position: absolute;
  left: 18px;
  bottom: 18px;
  z-index: 5;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.10);
  font-size: 12px;
  backdrop-filter: blur(12px);
}

.timeline-hud {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 18px;
  z-index: 6;
  pointer-events: auto;
}

.omnibox-layer {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: start center;
  padding-top: 64px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(6px);
}

@media (max-width: 980px) {
  .ide-aside {
    width: 320px;
  }
  .ide-aside.right {
    width: 360px;
  }
}

@media (max-width: 860px) {
  .ide-body {
    flex-direction: column;
  }
  .ide-aside,
  .ide-aside.right {
    width: 100%;
    height: 260px;
  }
}
</style>
