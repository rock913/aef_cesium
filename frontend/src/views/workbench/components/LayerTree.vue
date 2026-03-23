<template>
  <div class="tree" aria-label="Layer Tree">
    <div class="k">LAYER TREE</div>

    <div class="g" v-if="currentScale === 'earth'" aria-label="Earth Layers">
      <div class="gh">EARTH</div>
      <div class="item" v-for="(l, i) in earthLayers" :key="l.id">
        <div class="row">
          <label class="left">
            <input class="chk" type="checkbox" :checked="!!l.enabled" @change="toggle(l.id)" />
            <span class="name">{{ l.name }}</span>
          </label>
          <div class="ops" aria-label="Reorder">
            <button class="op" type="button" :disabled="i === 0" title="Move Up" @click="moveWithin('earth', l.id, -1)">↑</button>
            <button class="op" type="button" :disabled="i === earthLayers.length - 1" title="Move Down" @click="moveWithin('earth', l.id, 1)">↓</button>
          </div>
        </div>

        <div class="params" v-if="l && l.params" aria-label="Layer Params">
          <div class="param">
            <span class="pk">Opacity</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.02"
              :value="Number(l.params.opacity ?? 0.8)"
              @input="setParam(l.id, 'opacity', $event?.target?.value)"
            />
            <span class="pv">{{ fmtPct(l.params.opacity) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'anomaly-mask'">
            <span class="pk">Threshold</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.threshold ?? 0.1)"
              @input="setParam(l.id, 'threshold', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.threshold) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'anomaly-mask'">
            <span class="pk">Palette</span>
            <input
              class="txt"
              type="text"
              spellcheck="false"
              :value="String(l.params.palette || '')"
              placeholder="FF4D6D"
              @change="setParam(l.id, 'palette', $event?.target?.value)"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="g" v-if="currentScale === 'macro'" aria-label="Sky Layers">
      <div class="gh">SKY</div>
      <div class="item" v-for="(l, i) in macroLayers" :key="l.id">
        <div class="row">
          <label class="left">
            <input class="chk" type="checkbox" :checked="!!l.enabled" @change="toggle(l.id)" />
            <span class="name">{{ l.name }}</span>
          </label>
          <div class="ops" aria-label="Reorder">
            <button class="op" type="button" disabled title="Move Up">↑</button>
            <button class="op" type="button" disabled title="Move Down">↓</button>
          </div>
        </div>

        <div class="params" v-if="l && l.params" aria-label="Layer Params">
          <div class="param" v-if="String(l.id) === 'bloom'">
            <span class="pk">Strength</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="3"
              step="0.05"
              :value="Number(l.params.strength ?? 1.1)"
              @input="setParam(l.id, 'strength', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.strength) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'bloom'">
            <span class="pk">Threshold</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.threshold ?? 0.65)"
              @input="setParam(l.id, 'threshold', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.threshold) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'bloom'">
            <span class="pk">Radius</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.radius ?? 0.15)"
              @input="setParam(l.id, 'radius', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.radius) }}</span>
          </div>

          <div class="param" v-if="String(l.id).startsWith('astro-')">
            <span class="pk">Opacity</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.02"
              :value="Number(l.params.opacity ?? 1)"
              @input="setParam(l.id, 'opacity', $event?.target?.value)"
            />
            <span class="pv">{{ fmtPct(l.params.opacity) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === ASTRO_GIS_LAYER_IDS.MACRO_SDSS">
            <span class="pk">Point Size</span>
            <input
              class="rng"
              type="range"
              min="1"
              max="64"
              step="1"
              :value="Number(l.params.pointSize ?? 15)"
              @input="setParam(l.id, 'pointSize', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.pointSize) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND">
            <span class="pk">Survey</span>
            <input
              class="txt"
              type="text"
              spellcheck="false"
              :value="String(l.params.survey || '')"
              placeholder="P/DSS2/color"
              @change="setParam(l.id, 'survey', $event?.target?.value)"
            />
          </div>

          <div class="param" v-if="String(l.id) === ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND">
            <span class="pk">FOV Sync</span>
            <input
              class="chk"
              type="checkbox"
              :checked="l.params.fovSync === undefined ? true : !!l.params.fovSync"
              @change="setParam(l.id, 'fovSync', $event?.target?.checked)"
            />
            <span class="pv">{{ (l.params.fovSync === false) ? 'OFF' : 'ON' }}</span>
          </div>

          <div class="param" v-if="String(l.id) === ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD">
            <span class="pk">Max Rows</span>
            <input
              class="rng"
              type="range"
              min="50"
              max="2000"
              step="50"
              :value="Number(l.params.maxRows ?? 600)"
              @input="setParam(l.id, 'maxRows', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.maxRows) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'micro-atoms'">
            <span class="pk">Opacity</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.02"
              :value="Number(l.params.opacity ?? 0.85)"
              @input="setParam(l.id, 'opacity', $event?.target?.value)"
            />
            <span class="pv">{{ fmtPct(l.params.opacity) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'micro-atoms'">
            <span class="pk">Transmission</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.transmission ?? 0.85)"
              @input="setParam(l.id, 'transmission', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.transmission) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'micro-atoms'">
            <span class="pk">IOR</span>
            <input
              class="rng"
              type="range"
              min="1"
              max="2"
              step="0.01"
              :value="Number(l.params.ior ?? 1.4)"
              @input="setParam(l.id, 'ior', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.ior) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="g" v-if="currentScale === 'micro'" aria-label="Micro Layers">
      <div class="gh">MICRO</div>
      <div class="item" v-for="(l, i) in microLayers" :key="l.id">
        <div class="row">
          <label class="left">
            <input class="chk" type="checkbox" :checked="!!l.enabled" @change="toggle(l.id)" />
            <span class="name">{{ l.name }}</span>
          </label>
          <div class="ops" aria-label="Reorder">
            <button class="op" type="button" disabled title="Move Up">↑</button>
            <button class="op" type="button" disabled title="Move Down">↓</button>
          </div>
        </div>

        <div class="params" v-if="l && l.params" aria-label="Layer Params">
          <div class="param" v-if="String(l.id) === 'bloom'">
            <span class="pk">Strength</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="3"
              step="0.05"
              :value="Number(l.params.strength ?? 1.1)"
              @input="setParam(l.id, 'strength', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.strength) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'bloom'">
            <span class="pk">Threshold</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.threshold ?? 0.65)"
              @input="setParam(l.id, 'threshold', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.threshold) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'bloom'">
            <span class="pk">Radius</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.radius ?? 0.15)"
              @input="setParam(l.id, 'radius', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.radius) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'micro-atoms'">
            <span class="pk">Opacity</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.02"
              :value="Number(l.params.opacity ?? 0.85)"
              @input="setParam(l.id, 'opacity', $event?.target?.value)"
            />
            <span class="pv">{{ fmtPct(l.params.opacity) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'micro-atoms'">
            <span class="pk">Transmission</span>
            <input
              class="rng"
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="Number(l.params.transmission ?? 0.85)"
              @input="setParam(l.id, 'transmission', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.transmission) }}</span>
          </div>

          <div class="param" v-if="String(l.id) === 'micro-atoms'">
            <span class="pk">IOR</span>
            <input
              class="rng"
              type="range"
              min="1"
              max="2"
              step="0.01"
              :value="Number(l.params.ior ?? 1.4)"
              @input="setParam(l.id, 'ior', $event?.target?.value)"
            />
            <span class="pv">{{ fmtNum(l.params.ior) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ASTRO_GIS_LAYER_IDS } from '../../../stores/astroStore.js'

const props = defineProps({
  layers: { type: Array, default: () => [] },
  currentScale: { type: String, default: 'earth' },
})

const emit = defineEmits(['update:layers'])

function toggle(id) {
  const next = (props.layers || []).map((l) => (l.id === id ? { ...l, enabled: !l.enabled } : l))
  emit('update:layers', next)
}

const earthLayers = computed(() => {
  const ids = new Set(['gee-heatmap', 'boundaries', 'anomaly-mask', 'ai-imagery', 'ai-vector'])
  return (props.layers || []).filter((l) => ids.has(String(l?.id || '')))
})

const threeLayers = computed(() => {
  const ids = new Set([
    'bloom',
    'macro-spiral',
    'micro-atoms',
    ...Object.values(ASTRO_GIS_LAYER_IDS),
  ])
  return (props.layers || []).filter((l) => ids.has(String(l?.id || '')))
})

const macroLayers = computed(() => {
  const ids = new Set([
    'bloom',
    'macro-spiral',
    ASTRO_GIS_LAYER_IDS.MACRO_SDSS,
    ASTRO_GIS_LAYER_IDS.DEMO_CSST,
    ASTRO_GIS_LAYER_IDS.DEMO_GOTTA,
    ASTRO_GIS_LAYER_IDS.DEMO_INPAINT,
    ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND,
    ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD,
  ])
  return threeLayers.value.filter((l) => ids.has(String(l?.id || '')))
})

const microLayers = computed(() => {
  const ids = new Set(['bloom', 'micro-atoms'])
  return threeLayers.value.filter((l) => ids.has(String(l?.id || '')))
})

function moveWithin(group, id, dir) {
  // Only Earth layers participate in meaningful ordering today.
  const g = String(group || '')
  if (g !== 'earth') return

  const order = earthLayers.value.map((l) => l.id)
  const idx = order.indexOf(id)
  if (idx < 0) return
  const j = idx + (dir < 0 ? -1 : 1)
  if (j < 0 || j >= order.length) return

  const a = [...(props.layers || [])]
  const fullIdx = a.findIndex((l) => l.id === order[idx])
  const fullJ = a.findIndex((l) => l.id === order[j])
  if (fullIdx < 0 || fullJ < 0) return
  const tmp = a[fullIdx]
  a[fullIdx] = a[fullJ]
  a[fullJ] = tmp
  emit('update:layers', a)
}

function setParam(id, key, raw) {
  const k = String(key || '').trim()
  const next = (props.layers || []).map((l) => {
    if (l.id !== id) return l
    const params = { ...(l.params || {}) }
    if (k === 'opacity' || k === 'threshold' || k === 'strength' || k === 'radius' || k === 'transmission' || k === 'ior' || k === 'pointSize' || k === 'maxRows') {
      const n = Number(raw)
      if (Number.isFinite(n)) params[k] = n
      return { ...l, params }
    }
    if (k === 'palette') {
      params.palette = String(raw || '').trim()
      return { ...l, params }
    }
    if (k === 'survey') {
      params.survey = String(raw || '').trim()
      return { ...l, params }
    }
    if (k === 'fovSync') {
      params.fovSync = !!raw
      return { ...l, params }
    }
    return l
  })
  emit('update:layers', next)
}

function fmtPct(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return `${Math.round(Math.max(0, Math.min(1, n)) * 100)}%`
}

function fmtNum(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(2)
}
</script>

<style scoped>
.tree {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 14px;
  padding: 10px 10px;
  background: rgba(10, 15, 26, 0.20);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.k {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.78;
  font-weight: 900;
  margin-bottom: 8px;
}

.g {
  margin-top: 10px;
}

.g:first-of-type {
  margin-top: 0;
}

.gh {
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.70;
  font-weight: 900;
  margin: 2px 6px 6px;
}

.g.inactive {
  opacity: 0.45;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  padding: 6px 6px;
  border-radius: 10px;
}

.item {
  display: flex;
  flex-direction: column;
}

.params {
  margin: 0 6px 6px;
  padding: 8px 8px 8px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.param {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  margin-top: 6px;
}

.param:first-child {
  margin-top: 0;
}

.pk {
  width: 74px;
  opacity: 0.75;
  font-weight: 700;
}

.pv {
  width: 42px;
  text-align: right;
  opacity: 0.8;
  font-variant-numeric: tabular-nums;
}

.rng {
  flex: 1;
}

.txt {
  flex: 1;
  height: 24px;
  padding: 0 8px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: rgba(255, 255, 255, 0.90);
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.ops {
  display: flex;
  gap: 6px;
}

.op {
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
  color: rgba(255, 255, 255, 0.82);
  width: 22px;
  height: 20px;
  border-radius: 8px;
  cursor: pointer;
}

.op:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.op:hover:enabled {
  border-color: rgba(0, 240, 255, 0.30);
}

.row:hover {
  background: rgba(255, 255, 255, 0.06);
}

.chk {
  accent-color: rgba(0, 240, 255, 0.95);
}

.name {
  opacity: 0.92;
}
</style>
