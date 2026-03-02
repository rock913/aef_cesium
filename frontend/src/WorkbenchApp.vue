<template>
  <div class="wb" data-testid="workbench">
    <header class="wb-top">
      <div class="wb-brand">
        <div class="k">Zero2x</div>
        <div class="t">AI‑Native Workbench</div>
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
        <div class="pane-title">3D Preview</div>
        <div class="preview">
          Cesium / Charts 结果预览
          <div class="preview-sub">Next: mount selected mission output here</div>
        </div>

        <div class="pane-title" style="margin-top: 14px;">Interactive Papers</div>
        <div class="preview">
          Docs / Community
          <div class="preview-sub">Next: embed docs + citations + notebooks</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import MonacoLazyEditor from './components/MonacoLazyEditor.vue'

const code = ref(
  [
    '# Zero2x Workbench (MVP)',
    '# Goal: keep Landing fast; load Monaco only here.',
    '',
    'def analyze_poyang():',
    '    # TODO: connect backend datasets and produce insights',
    '    return {"status": "stub"}',
    '',
    'print(analyze_poyang())',
  ].join('\n')
)

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
  const plan = [
    'Agent (demo):',
    q ? `- Intent: ${q}` : '- Intent: Poyang wetland & bird migration analysis',
    '- Step 1: select datasets (wetland mask, hydrology time-series, migration tracks)',
    '- Step 2: compute trends + anomalies and generate evidence snippets',
    '- Step 3: render overlays in 3D preview and export a short report',
    '',
    'Tip: use /demo for visual validation; keep /workbench for workflows.',
  ].join('\n')

  _type(plan)
}

function reset() {
  agentText.value = 'System ready. Press Run to simulate an agent flow…'
}

onMounted(() => {
  try {
    document.body.style.overflow = 'hidden'
  } catch (_) {
    // ignore
  }

  try {
    lastIntent.value = window.sessionStorage?.getItem?.('z2x:lastIntent') || ''
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
