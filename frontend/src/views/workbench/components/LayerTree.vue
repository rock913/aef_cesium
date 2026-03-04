<template>
  <div class="tree" aria-label="Layer Tree">
    <div class="k">LAYER TREE</div>
    <div class="item" v-for="(l, i) in layers" :key="l.id">
      <div class="row">
        <label class="left">
          <input class="chk" type="checkbox" :checked="!!l.enabled" @change="toggle(l.id)" />
          <span class="name">{{ l.name }}</span>
        </label>
        <div class="ops" aria-label="Reorder">
          <button class="op" type="button" :disabled="i === 0" title="Move Up" @click="move(l.id, -1)">↑</button>
          <button class="op" type="button" :disabled="i === layers.length - 1" title="Move Down" @click="move(l.id, 1)">↓</button>
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
</template>

<script setup>
const props = defineProps({
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:layers'])

function toggle(id) {
  const next = (props.layers || []).map((l) => (l.id === id ? { ...l, enabled: !l.enabled } : l))
  emit('update:layers', next)
}

function move(id, dir) {
  const arr = [...(props.layers || [])]
  const idx = arr.findIndex((l) => l.id === id)
  if (idx < 0) return
  const j = idx + (dir < 0 ? -1 : 1)
  if (j < 0 || j >= arr.length) return
  const tmp = arr[idx]
  arr[idx] = arr[j]
  arr[j] = tmp
  emit('update:layers', arr)
}

function setParam(id, key, raw) {
  const k = String(key || '').trim()
  const next = (props.layers || []).map((l) => {
    if (l.id !== id) return l
    const params = { ...(l.params || {}) }
    if (k === 'opacity' || k === 'threshold') {
      const n = Number(raw)
      if (Number.isFinite(n)) params[k] = n
      return { ...l, params }
    }
    if (k === 'palette') {
      params.palette = String(raw || '').trim()
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
  position: absolute;
  right: 18px;
  top: 18px;
  z-index: 8;
  width: 220px;
  border-radius: 14px;
  padding: 10px 10px;
  background: rgba(10, 15, 26, 0.40);
  border: 1px solid rgba(255, 255, 255, 0.10);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 18px 55px rgba(0, 0, 0, 0.55);
}

.k {
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.78;
  font-weight: 900;
  margin-bottom: 8px;
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
