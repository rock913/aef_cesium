<template>
  <div class="galaxy" data-testid="data-galaxy">
    <div class="galaxy-top">
      <div class="galaxy-title">Semantic Galaxy (MVP)</div>
      <div class="galaxy-sub">{{ nodes.length }} nodes · {{ clusters.length }} clusters · Search → focus</div>

      <div class="galaxy-search">
        <input
          v-model="q"
          class="galaxy-input"
          type="text"
          placeholder="Search cluster: wetlands / hydrology / migration / 鄱阳湖…"
          @keydown.enter.prevent="applyQuery"
          aria-label="Data galaxy search"
        />
        <button class="galaxy-btn" type="button" @click="applyQuery">Focus</button>
        <button class="galaxy-btn secondary" type="button" @click="resetFocus">Reset</button>
      </div>

      <div v-if="activeCluster" class="galaxy-hint">
        Focus: <span class="pill">{{ activeCluster.name }}</span>
        <span class="sep">·</span>
        <span class="k">Tip</span>
        <span class="v">Try: "poyang", "湿地", "hydrology"</span>
      </div>
    </div>

    <div class="galaxy-canvas-wrap">
      <canvas ref="canvasEl" class="galaxy-canvas" />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  computeClusterStats,
  defaultGalaxyClusters,
  generateGalaxyNodes,
  matchGalaxyQuery,
} from '../utils/galaxy.js'

const canvasEl = ref(null)

const clusters = defaultGalaxyClusters()
const nodes = generateGalaxyNodes({ seed: 21, count: 900, clusters })
const stats = computeClusterStats(nodes, clusters)

const q = ref('')
const activeClusterId = ref('')

const activeCluster = computed(() => {
  const id = activeClusterId.value
  return id ? stats[id] : null
})

const cam = {
  x: 0,
  y: 0,
  zoom: 1.0,
  tx: 0,
  ty: 0,
  tzoom: 1.0,
}

let _raf = 0
let _ctx = null
let _dpr = 1

function _resize() {
  const el = canvasEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const w = Math.max(1, Math.floor(rect.width))
  const h = Math.max(1, Math.floor(rect.height))
  _dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1))

  el.width = Math.floor(w * _dpr)
  el.height = Math.floor(h * _dpr)

  if (_ctx) {
    _ctx.setTransform(_dpr, 0, 0, _dpr, 0, 0)
  }
}

function _lerp(a, b, t) {
  return a + (b - a) * t
}

function _toScreen(n, w, h) {
  const sx = (n.x - cam.x) * cam.zoom * 360 + w / 2
  const sy = (n.y - cam.y) * cam.zoom * 360 + h / 2
  return { sx, sy }
}

function _draw() {
  const el = canvasEl.value
  if (!el || !_ctx) return

  const w = el.width / _dpr
  const h = el.height / _dpr

  // Ease camera
  cam.x = _lerp(cam.x, cam.tx, 0.08)
  cam.y = _lerp(cam.y, cam.ty, 0.08)
  cam.zoom = _lerp(cam.zoom, cam.tzoom, 0.08)

  _ctx.clearRect(0, 0, w, h)

  // Background glow
  const g = _ctx.createRadialGradient(w * 0.5, h * 0.4, 20, w * 0.5, h * 0.5, Math.max(w, h) * 0.7)
  g.addColorStop(0, 'rgba(120,160,255,0.14)')
  g.addColorStop(0.35, 'rgba(0,0,0,0)')
  g.addColorStop(1, 'rgba(0,0,0,0)')
  _ctx.fillStyle = g
  _ctx.fillRect(0, 0, w, h)

  // Draw nodes
  const focusId = activeClusterId.value

  for (let i = 0; i < nodes.length; i += 1) {
    const n = nodes[i]
    const { sx, sy } = _toScreen(n, w, h)
    if (sx < -20 || sy < -20 || sx > w + 20 || sy > h + 20) continue

    const isFocus = focusId && n.clusterId === focusId
    const hue = stats[n.clusterId]?.hue ?? 210

    const r = isFocus ? (2.1 + n.mass * 18) : (1.2 + n.mass * 12)
    const a = isFocus ? 0.92 : 0.42

    _ctx.beginPath()
    _ctx.fillStyle = `hsla(${hue}, 90%, 70%, ${a})`
    _ctx.arc(sx, sy, r, 0, Math.PI * 2)
    _ctx.fill()
  }

  // Cluster labels
  _ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
  _ctx.textBaseline = 'top'

  for (const c of clusters) {
    const s = stats[c.id]
    if (!s || !s.count) continue

    const { sx, sy } = _toScreen({ x: s.cx, y: s.cy }, w, h)
    if (sx < -80 || sy < -40 || sx > w + 80 || sy > h + 60) continue

    const isActive = focusId === c.id
    const hue = s.hue

    _ctx.fillStyle = isActive ? `hsla(${hue}, 95%, 75%, 0.95)` : 'rgba(255,255,255,0.55)'
    _ctx.fillText(c.name, sx + 10, sy + 8)

    _ctx.beginPath()
    _ctx.strokeStyle = isActive ? `hsla(${hue}, 95%, 75%, 0.55)` : 'rgba(255,255,255,0.14)'
    _ctx.lineWidth = isActive ? 2 : 1
    _ctx.arc(sx, sy, isActive ? 10 : 7, 0, Math.PI * 2)
    _ctx.stroke()
  }

  _raf = window.requestAnimationFrame(_draw)
}

function applyQuery() {
  const id = matchGalaxyQuery(q.value, clusters)
  if (!id) return
  activeClusterId.value = id

  const s = stats[id]
  if (s) {
    cam.tx = s.cx
    cam.ty = s.cy
    cam.tzoom = 1.85
  }
}

function resetFocus() {
  activeClusterId.value = ''
  cam.tx = 0
  cam.ty = 0
  cam.tzoom = 1.0
}

onMounted(() => {
  try {
    const el = canvasEl.value
    if (!el) return
    _ctx = el.getContext('2d', { alpha: true })
    _resize()

    window.addEventListener('resize', _resize, { passive: true })

    // Start subtle drift
    cam.tx = 0
    cam.ty = 0
    cam.tzoom = 1.0

    _raf = window.requestAnimationFrame(_draw)
  } catch (_) {
    // ignore
  }
})

onBeforeUnmount(() => {
  try {
    if (_raf) window.cancelAnimationFrame(_raf)
  } catch (_) {
    // ignore
  }
  try {
    window.removeEventListener('resize', _resize)
  } catch (_) {
    // ignore
  }
})
</script>

<style scoped>
.galaxy {
  margin-top: 18px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.galaxy-top {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.galaxy-title {
  font-weight: 900;
  letter-spacing: 0.4px;
}

.galaxy-sub {
  font-size: 12px;
  opacity: 0.72;
}

.galaxy-search {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.galaxy-input {
  flex: 1;
  min-width: min(360px, 100%);
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #eef2ff;
  outline: none;
}

.galaxy-input:focus {
  border-color: rgba(120, 160, 255, 0.7);
  box-shadow: 0 0 0 4px rgba(120, 160, 255, 0.18);
}

.galaxy-btn {
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(120, 160, 255, 0.18);
  border: 1px solid rgba(120, 160, 255, 0.35);
  color: #eef2ff;
  cursor: pointer;
}

.galaxy-btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.16);
}

.galaxy-hint {
  font-size: 12px;
  opacity: 0.86;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.sep {
  margin: 0 8px;
  opacity: 0.55;
}

.k {
  opacity: 0.7;
}

.v {
  opacity: 0.9;
}

.galaxy-canvas-wrap {
  margin-top: 12px;
  width: 100%;
  height: 360px;
  border-radius: 16px;
  overflow: hidden;
  background: radial-gradient(800px 520px at 30% 20%, rgba(0, 255, 255, 0.06), transparent 60%),
    radial-gradient(920px 680px at 70% 50%, rgba(255, 120, 120, 0.06), transparent 60%),
    linear-gradient(180deg, rgba(0, 0, 0, 0.35), rgba(0, 0, 0, 0.18));
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.galaxy-canvas {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
