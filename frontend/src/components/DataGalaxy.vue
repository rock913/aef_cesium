<template>
  <div class="galaxy" data-testid="data-galaxy">
    <div ref="wrapEl" class="galaxy-wrap" aria-label="Autonomous semantic galaxy">
      <div ref="webglEl" class="webgl" aria-hidden="true" />
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const wrapEl = ref(null)
const webglEl = ref(null)

// The three core clusters (kept small & explicit so copy remains stable).
const clusters = Object.freeze([
  {
    id: 'geo',
    name: 'Geo & Hydrology',
    meta: '鄱阳湖水文 / 地质演变',
    hex: '#00F0FF',
    color: 0x00F0FF,
    center: { x: 25, y: 10, z: -15 },
    nodes: 4500,
  },
  {
    id: 'bio',
    name: 'OneGenome Sequences',
    meta: 'OneGenome 基因序列 / 注意力机制',
    hex: '#9D4EDD',
    color: 0x9D4EDD,
    center: { x: -20, y: -15, z: 10 },
    nodes: 3200,
  },
  {
    id: 'mat',
    name: 'Porous Materials',
    meta: '航天多孔合金 / 热力学',
    hex: '#FF6B00',
    color: 0xFF6B00,
    center: { x: 5, y: 20, z: 25 },
    nodes: 2800,
  },
])

let THREE = null
let scene = null
let camera = null
let renderer = null
let galaxy = null
let connections = null
let lookAtTarget = null
let _raf = 0
let _resizeUnsub = null

const _state = {
  t0: 0,
  stepStart: 0,
  stepIndex: 0,
  running: false,
}

function _prefersReducedMotion() {
  try {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch (_) {
    return false
  }
}

function _easeInOutQuad(t) {
  const x = Math.max(0, Math.min(1, Number(t) || 0))
  return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2
}

function _lerp(a, b, t) {
  return a + (b - a) * t
}

function _createGlowTexture() {
  const canvas = document.createElement('canvas')
  canvas.width = 64
  canvas.height = 64
  const ctx = canvas.getContext('2d')
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32)
  g.addColorStop(0, 'rgba(255,255,255,1)')
  g.addColorStop(0.2, 'rgba(255,255,255,0.85)')
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 64, 64)
  return new THREE.CanvasTexture(canvas)
}

function _buildGalaxyPoints(total = 18000) {
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(total * 3)
  const colors = new Float32Array(total * 3)
  const sizes = new Float32Array(total)

  const white = new THREE.Color(0xffffff)
  const dark = new THREE.Color(0x2a3a5a)

  for (let i = 0; i < total; i += 1) {
    let px = 0
    let py = 0
    let pz = 0
    let size = Math.random() * 0.5 + 0.2
    let finalColor = dark

    if (Math.random() < 0.85) {
      const c = clusters[Math.floor(Math.random() * clusters.length)]
      const center = new THREE.Vector3(c.center.x, c.center.y, c.center.z)
      const radius = Math.pow(Math.random(), 2.5) * 20
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      px = center.x + radius * Math.sin(phi) * Math.cos(theta)
      py = center.y + radius * Math.sin(phi) * Math.sin(theta)
      pz = center.z + radius * Math.cos(phi)

      finalColor = new THREE.Color(c.color).lerp(white, Math.random() * 0.4)
      size = Math.random() * 1.5 + 0.5
    } else {
      px = (Math.random() - 0.5) * 120
      py = (Math.random() - 0.5) * 120
      pz = (Math.random() - 0.5) * 120
      finalColor = dark
    }

    positions[i * 3] = px
    positions[i * 3 + 1] = py
    positions[i * 3 + 2] = pz

    colors[i * 3] = finalColor.r
    colors[i * 3 + 1] = finalColor.g
    colors[i * 3 + 2] = finalColor.b

    sizes[i] = size
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  const material = new THREE.ShaderMaterial({
    uniforms: { pointTexture: { value: _createGlowTexture() } },
    vertexShader: `
      attribute float size;
      attribute vec3 color;
      varying vec3 vColor;
      void main() {
        vColor = color;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * (120.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      uniform sampler2D pointTexture;
      varying vec3 vColor;
      void main() {
        gl_FragColor = vec4(vColor, 1.0) * texture2D(pointTexture, gl_PointCoord);
      }
    `,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    transparent: true,
  })

  const points = new THREE.Points(geometry, material)
  return points
}

function _buildConnections() {
  const pts = clusters.map((c) => new THREE.Vector3(c.center.x, c.center.y, c.center.z))
  const geo = new THREE.BufferGeometry().setFromPoints([pts[0], pts[1], pts[2], pts[0]])
  const mat = new THREE.LineBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.15,
    blending: THREE.AdditiveBlending,
  })
  return new THREE.Line(geo, mat)
}

function _getTourSequence() {
  const viewFar = {
    pos: new THREE.Vector3(0, 0, 90),
    target: new THREE.Vector3(0, 0, 0),
    durationMs: 5200,
    holdMs: 1200,
  }

  const closeups = clusters.map((c) => {
    const center = new THREE.Vector3(c.center.x, c.center.y, c.center.z)
    const dir = center.clone().normalize().multiplyScalar(20)
    return {
      pos: center.clone().add(dir),
      target: center,
      durationMs: 4200,
      holdMs: 1500,
    }
  })

  return [viewFar, closeups[0], closeups[1], closeups[2], viewFar]
}

function _advanceTour(now) {
  if (!_state.running || !camera || !lookAtTarget) return
  const seq = _getTourSequence()
  const step = seq[_state.stepIndex % seq.length]
  if (!step) return

  if (!_state.stepStart) _state.stepStart = now
  const t = (now - _state.stepStart) / Math.max(1, step.durationMs)

  if (t >= 1) {
    camera.position.copy(step.pos)
    lookAtTarget.copy(step.target)

    if (!_state._holdUntil) _state._holdUntil = now + (step.holdMs || 0)
    if (now >= _state._holdUntil) {
      _state.stepIndex += 1
      _state.stepStart = now
      _state._holdUntil = 0
    }
    return
  }

  const e = _easeInOutQuad(t)
  // Smoothly interpolate camera + target.
  // We keep previous values by blending from current towards the step target.
  camera.position.set(
    _lerp(camera.position.x, step.pos.x, e),
    _lerp(camera.position.y, step.pos.y, e),
    _lerp(camera.position.z, step.pos.z, e)
  )
  lookAtTarget.set(
    _lerp(lookAtTarget.x, step.target.x, e),
    _lerp(lookAtTarget.y, step.target.y, e),
    _lerp(lookAtTarget.z, step.target.z, e)
  )
}

function _onResize() {
  const root = wrapEl.value
  if (!root || !camera || !renderer) return
  const rect = root.getBoundingClientRect()
  const w = Math.max(1, Math.floor(rect.width))
  const h = Math.max(1, Math.floor(rect.height))
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
}

function _tick(now) {
  _raf = window.requestAnimationFrame(_tick)
  if (!renderer || !scene || !camera) return

  const t = Number(now || 0)

  if (!_prefersReducedMotion()) {
    _advanceTour(t)
  }

  try {
    camera.lookAt(lookAtTarget)
  } catch (_) {
    // ignore
  }

  // Make the galaxy breathe subtly.
  if (galaxy) {
    galaxy.rotation.y += 0.0003
    galaxy.rotation.z += 0.0001
  }
  if (connections) {
    connections.rotation.y += 0.0003
    connections.rotation.z += 0.0001
  }
  renderer.render(scene, camera)
}

async function _init() {
  const host = webglEl.value
  const root = wrapEl.value
  if (!host || !root) return

  try {
    const mod = await import('three')
    THREE = mod
  } catch (_) {
    return
  }

  const rect = root.getBoundingClientRect()
  const w = Math.max(1, Math.floor(rect.width))
  const h = Math.max(1, Math.floor(rect.height))

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x020306)
  scene.fog = new THREE.FogExp2(0x020306, 0.012)

  camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000)
  camera.position.set(0, 0, 80)
  lookAtTarget = new THREE.Vector3(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  host.innerHTML = ''
  host.appendChild(renderer.domElement)

  // Particle count: scale down a bit on smaller viewports.
  const particleCount = w * h < 900 * 520 ? 12000 : 18000
  galaxy = _buildGalaxyPoints(particleCount)
  connections = _buildConnections()
  scene.add(galaxy)
  scene.add(connections)

  _state.running = true
  _state.stepStart = 0
  _state.stepIndex = 0
  _state._holdUntil = 0

  // Start render loop.
  _raf = window.requestAnimationFrame(_tick)

  const onResize = () => _onResize()
  window.addEventListener('resize', onResize, { passive: true })
  _resizeUnsub = () => {
    try {
      window.removeEventListener('resize', onResize)
    } catch (_) {
      // ignore
    }
  }
}

function _dispose() {
  _state.running = false
  if (_raf) {
    try {
      window.cancelAnimationFrame(_raf)
    } catch (_) {
      // ignore
    }
  }
  _raf = 0

  try {
    _resizeUnsub && _resizeUnsub()
  } catch (_) {
    // ignore
  }
  _resizeUnsub = null

  try {
    if (galaxy) {
      galaxy.geometry?.dispose?.()
      galaxy.material?.dispose?.()
    }
  } catch (_) {
    // ignore
  }

  try {
    if (connections) {
      connections.geometry?.dispose?.()
      connections.material?.dispose?.()
    }
  } catch (_) {
    // ignore
  }

  galaxy = null
  connections = null

  try {
    renderer?.dispose?.()
  } catch (_) {
    // ignore
  }
  renderer = null

  try {
    const host = webglEl.value
    if (host) host.innerHTML = ''
  } catch (_) {
    // ignore
  }

  scene = null
  camera = null
  lookAtTarget = null
}

onMounted(() => {
  _init()
})

onBeforeUnmount(() => {
  _dispose()
})
</script>

<style scoped>
.galaxy {
  width: 100%;
  height: 100%;
}

.galaxy-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #020306;
}

.webgl {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
