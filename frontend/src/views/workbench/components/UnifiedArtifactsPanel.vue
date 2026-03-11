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
            <button class="preset-btn" type="button" @click="onInsertWindPreset">WIND PRESET</button>
            <button class="run-btn" type="button" @click="onRunCode">▶ RUN SCRIPT</button>
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
import { computed, ref } from 'vue'
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

function onInsertWindPreset() {
  // Compute-only WGSL snippet (EngineRouter will wrap/augment render entrypoints).
  // Designed to be visually obvious with preset=wind (surface-like seeding + higher stepScale).
  const code = `// WGSL compute body snippet: procedural wind on a sphere (demo-safe)
// Requires bindings (group(0)): particles (binding(0) storage rw vec4 array), particles_ro (binding(3) storage read vec4 array), uParams (binding(2) vec4: t, stepScale, _, _)
let i = gid.x;
let n = arrayLength(&particles.data);
if (i >= n) { return; }

let t = uParams.x;
let s = max(0.0, uParams.y);

var p = particles.data[i];
let r = length(p.xyz);
if (r < 1.0) { return; }

let up = normalize(p.xyz);
let PI = 3.14159265;
let TAU = 6.2831853;

// NOTE: 'ref' is a reserved keyword in newer WGSL parsers.
var axisRef = vec3<f32>(0.0, 0.0, 1.0);
if (abs(up.z) > 0.9) { axisRef = vec3<f32>(0.0, 1.0, 0.0); }
let east = normalize(cross(axisRef, up));
let north = normalize(cross(up, east));

// Build a cyclone-rich tangent flow in lon/lat space.
let lat = asin(clamp(up.z, -1.0, 1.0));
let lon = atan2(up.y, up.x);

// Zonal jet bands + meanders.
let jet = cos(lat * 6.0) * 1.25;
let meander = sin(lon * 3.0 + t * 0.9 + lat * 2.0) * 0.65;

// Two moving vortex centers (in lon/lat).
let c1 = vec2<f32>(0.85 * sin(t * 0.35), 0.45 * sin(t * 0.27));
let c2 = vec2<f32>(1.70 * cos(t * 0.23 + 1.0), -0.55 * cos(t * 0.19));

var d1 = vec2<f32>(lon - c1.x, lat - c1.y);
var d2 = vec2<f32>(lon - c2.x, lat - c2.y);

// Wrap lon deltas to [-PI, PI] for continuity across the date line.
d1.x = d1.x - select(0.0, TAU, d1.x > PI);
d1.x = d1.x + select(0.0, TAU, d1.x < -PI);
d2.x = d2.x - select(0.0, TAU, d2.x > PI);
d2.x = d2.x + select(0.0, TAU, d2.x < -PI);

let inv1 = 1.0 / (dot(d1, d1) + 0.07);
let inv2 = 1.0 / (dot(d2, d2) + 0.06);
let swirl1 = vec2<f32>(-d1.y, d1.x) * inv1 * 2.6;
let swirl2 = vec2<f32>(-d2.y, d2.x) * inv2 * 2.2;

let u = (jet + meander) + swirl1.x + swirl2.x;
let v = (swirl1.y + swirl2.y) - sin(lat * 3.0) * 0.55;
let vel = east * u + north * v;

// Advect along tangent and re-project to a stable radius (cinematic shell).
let adv = vel * (s * 80000.0);
p.xyz = normalize(p.xyz + adv) * 20000000.0;
particles.data[i] = p;`;

  try {
    codeModel.value = code
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
}

.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
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

.preset-btn {
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
}

.preset-btn:hover {
  border-color: rgba(0, 240, 255, 0.28);
  background: rgba(0, 240, 255, 0.08);
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
  min-height: 240px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.10);
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
