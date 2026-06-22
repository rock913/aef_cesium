<template>
  <div
    ref="rootEl"
    class="hero-visual"
    aria-hidden="true"
    data-hero-visual="true"
    :data-hero-state="heroState"
    :data-hero-assets="heroAssets"
  >
    <div v-if="showDebugBadge" class="hero-debug" aria-hidden="true">
      <div class="k">Hero</div>
      <div class="v">state: {{ heroState }}</div>
      <div class="v">assets: {{ heroAssets }}</div>
    </div>
    <!--
      Optional design-driven A-plan assets.
      Designers can drop files into /public/zero2x/hero/ without touching code.
      If files are missing (404), we quietly fall back to CSS + Three.js.
    -->
    <video
      v-if="showStardustVideo"
      class="asset stardust"
      :src="stardustVideoSrc"
      autoplay
      muted
      loop
      playsinline
      preload="metadata"
      @error="onStardustVideoError"
    />
    <img
      v-else-if="showStardustImg"
      class="asset stardust"
      :src="stardustImgSrc"
      alt=""
      loading="lazy"
      decoding="async"
      @error="onStardustImgError"
    />

    <video
      v-if="showSphereVideo"
      class="asset sphere"
      :src="sphereVideoSrc"
      autoplay
      muted
      loop
      playsinline
      preload="metadata"
      @error="onSphereVideoError"
    />
    <img
      v-else-if="showSphereImg"
      class="asset sphere"
      :src="sphereImgSrc"
      alt=""
      loading="lazy"
      decoding="async"
      @error="onSphereImgError"
    />

    <div class="fallback" />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

const rootEl = ref(null)

const stardustVideoSrc = '/zero2x/hero/stardust_bg.webm'
const stardustImgSrc = '/zero2x/hero/stardust_bg.webp'
const sphereVideoSrc = '/zero2x/hero/glow_sphere.webm'
const sphereImgSrc = '/zero2x/hero/glow_sphere.webp'

const showStardustVideo = ref(true)
const showStardustImg = ref(true)
const showSphereVideo = ref(true)
const showSphereImg = ref(true)

const heroState = ref('init')
const heroAssets = ref('pending')
const showDebugBadge = ref(false)

let rafId = 0
let resizeObserver = null
let cleanupFn = null

function hasWebGL() {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl') || c.getContext('experimental-webgl'))
  } catch (_) {
    return false
  }
}

function _debug(msg) {
  try {
    // Keep logs quiet in prod; useful during dev.
    if (!import.meta?.env?.DEV) return
    // eslint-disable-next-line no-console
    console.debug(`[HeroVisual] ${msg}`)
  } catch (_) {
    // ignore
  }
}

function _setState(s) {
  heroState.value = String(s || 'init')
}

function _updateAssetsState() {
  // Best-effort: infer whether A-plan assets are present based on v-if state.
  // If assets are missing, video/img elements may still exist briefly until error fires.
  const hasAny = !!(
    showStardustVideo.value ||
    showStardustImg.value ||
    showSphereVideo.value ||
    showSphereImg.value
  )
  heroAssets.value = hasAny ? 'attempting' : 'none'
}

function hasDebugHeroFlag() {
  try {
    const url = new URL(window.location.href)
    if (url.searchParams?.has?.('debughero')) return true

    const hash = String(window.location.hash || '')
    // Support patterns like `/#/?debughero=1` (query string inside hash).
    const qIndex = hash.indexOf('?')
    if (qIndex >= 0) {
      const maybeQuery = hash.slice(qIndex + 1)
      const sp = new URLSearchParams(maybeQuery)
      if (sp.has('debughero')) return true
    }
  } catch (_) {
    // ignore
  }
  return false
}

function onStardustVideoError() {
  showStardustVideo.value = false
  _updateAssetsState()
}

function onStardustImgError() {
  showStardustImg.value = false
  _updateAssetsState()
}

function onSphereVideoError() {
  showSphereVideo.value = false
  _updateAssetsState()
}

function onSphereImgError() {
  showSphereImg.value = false
  _updateAssetsState()
}

async function mountThree() {
  const host = rootEl.value
  if (!host) return
  if (typeof window === 'undefined') return
  if (!hasWebGL()) {
    _setState('no-webgl')
    _debug('disabled: WebGL not available')
    return
  }

  _setState('three-loading')
  _debug('loading three.js')

  // Optional A-plan assets (design can drop files into `public/zero2x/hero/`)
  // If those files are present later, we can add a <video>/<img> layer here.

  const {
    Scene,
    FogExp2,
    PerspectiveCamera,
    WebGLRenderer,
    Group,
    ACESFilmicToneMapping,
    BufferGeometry,
    BufferAttribute,
    Float32BufferAttribute,
    Color,
    Points,
    PointsMaterial,
    AdditiveBlending,
    CanvasTexture,
    SpriteMaterial,
    Sprite,
    LineSegments,
    LineBasicMaterial,
  } = await import('three')

  const canvas = document.createElement('canvas')
  canvas.className = 'hero-canvas'
  canvas.setAttribute('aria-hidden', 'true')
  host.appendChild(canvas)

  _setState('three-mounted')
  _debug('three.js mounted')

  const scene = new Scene()
  // Keep it very dark; fog adds depth and hides hard edges.
  scene.fog = new FogExp2('#030409', 0.03)

  const camera = new PerspectiveCamera(60, 1, 0.1, 100)
  camera.position.z = 7

  const renderer = new WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: false
  })

  renderer.setClearColor(0x000000, 0)
  // Compress highlights to avoid center blowout under additive blending.
  // Keeps the “bloomy” feel but preserves UI legibility.
  renderer.toneMapping = ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0

  // =========================================================
  // V2 Hero: stardust + dense nebula core + neural skeleton
  // Inspired by the provided prototype (Issue #14 visual pack).
  // =========================================================

  // Background stardust (subtle, small, additive)
  const stardustGeo = new BufferGeometry()
  const stardustCount = 3000
  const stardustPos = new Float32Array(stardustCount * 3)
  for (let i = 0; i < stardustCount * 3; i++) {
    stardustPos[i] = (Math.random() - 0.5) * 40
  }
  stardustGeo.setAttribute('position', new BufferAttribute(stardustPos, 3))

  const stardustMat = new PointsMaterial({
    color: 0x3a4a6a,
    size: 0.03,
    transparent: true,
    opacity: 0.3,
    blending: AdditiveBlending,
    depthWrite: false
  })

  const stardust = new Points(stardustGeo, stardustMat)
  stardust.position.z = -5
  scene.add(stardust)

  const sphereGroup = new Group()
  scene.add(sphereGroup)

  const radius = 2.8
  const colorCyan = new Color('#00F0FF')
  const colorPurple = new Color('#9D4EDD')

  // Core glow sprite (cheap bloom-like feel without post-processing)
  const glowCanvas = document.createElement('canvas')
  glowCanvas.width = 256
  glowCanvas.height = 256
  const ctx = glowCanvas.getContext('2d')
  if (ctx) {
    const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128)
    // Very weak center glow: acts like ambient “airlight”, not a supernova.
    g.addColorStop(0, 'rgba(0, 240, 255, 0.08)')
    g.addColorStop(0.4, 'rgba(157, 78, 221, 0.05)')
    g.addColorStop(1, 'rgba(0, 0, 0, 0)')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, 256, 256)
  }
  const glowTexture = new CanvasTexture(glowCanvas)
  const glowMaterial = new SpriteMaterial({
    map: glowTexture,
    color: 0xffffff,
    transparent: true,
    blending: AdditiveBlending,
    opacity: 1.0,
    depthWrite: false
  })
  const glowSprite = new Sprite(glowMaterial)
  glowSprite.scale.set(radius * 2.5, radius * 2.5, 1)
  sphereGroup.add(glowSprite)

  // Dense nebula shell (Dyson shell): no center points -> no white blowout.
  const denseCount = 8000
  const densePos = new Float32Array(denseCount * 3)
  const denseCol = new Float32Array(denseCount * 3)

  for (let i = 0; i < denseCount; i++) {
    const u = Math.random()
    const v = Math.random()
    const theta = u * 2.0 * Math.PI
    const phi = Math.acos(2.0 * v - 1.0)

    // Dyson shell: force an inner radius so no particles exist near (0,0,0).
    const innerRadius = radius * 0.65
    const r = innerRadius + (radius - innerRadius) * Math.random()

    const x = r * Math.sin(phi) * Math.cos(theta)
    const y = r * Math.sin(phi) * Math.sin(theta)
    const z = r * Math.cos(phi)

    densePos[i * 3] = x
    densePos[i * 3 + 1] = y
    densePos[i * 3 + 2] = z

    const mixRatio = (y + radius) / (radius * 2)
    const c = colorCyan.clone().lerp(colorPurple, Math.min(1, Math.max(0, mixRatio)))
    // No artificial center brightening; the shell’s natural overlap is enough.
    denseCol[i * 3] = c.r
    denseCol[i * 3 + 1] = c.g
    denseCol[i * 3 + 2] = c.b
  }

  const denseGeo = new BufferGeometry()
  denseGeo.setAttribute('position', new BufferAttribute(densePos, 3))
  denseGeo.setAttribute('color', new BufferAttribute(denseCol, 3))

  const denseMat = new PointsMaterial({
    size: 0.025,
    vertexColors: true,
    transparent: true,
    opacity: 0.35,
    blending: AdditiveBlending,
    depthWrite: false
  })

  const denseSystem = new Points(denseGeo, denseMat)
  sphereGroup.add(denseSystem)

  // Sparse neural skeleton + lines (kept small for perf)
  const neuralCount = 300
  const neuralPos = new Float32Array(neuralCount * 3)
  const neuralCol = new Float32Array(neuralCount * 3)

  for (let i = 0; i < neuralCount; i++) {
    const u = Math.random()
    const v = Math.random()
    const theta = u * 2.0 * Math.PI
    const phi = Math.acos(2.0 * v - 1.0)
    // Neural nodes also live on an outer shell to prevent center line overdraw.
    const innerRadius = radius * 0.7
    const r = innerRadius + (radius - innerRadius) * Math.random()

    const x = r * Math.sin(phi) * Math.cos(theta)
    const y = r * Math.sin(phi) * Math.sin(theta)
    const z = r * Math.cos(phi)

    neuralPos[i * 3] = x
    neuralPos[i * 3 + 1] = y
    neuralPos[i * 3 + 2] = z

    const mixRatio = (y + radius) / (radius * 2)
    const c = colorCyan.clone().lerp(colorPurple, Math.min(1, Math.max(0, mixRatio)))
    neuralCol[i * 3] = c.r
    neuralCol[i * 3 + 1] = c.g
    neuralCol[i * 3 + 2] = c.b
  }

  const linePos = []
  const lineCol = []
  const threshold = 1.2
  const thresholdSq = threshold * threshold

  for (let i = 0; i < neuralCount; i++) {
    const ix = neuralPos[i * 3]
    const iy = neuralPos[i * 3 + 1]
    const iz = neuralPos[i * 3 + 2]

    const ir = neuralCol[i * 3]
    const ig = neuralCol[i * 3 + 1]
    const ib = neuralCol[i * 3 + 2]

    for (let j = i + 1; j < neuralCount; j++) {
      const jx = neuralPos[j * 3]
      const jy = neuralPos[j * 3 + 1]
      const jz = neuralPos[j * 3 + 2]

      const dx = ix - jx
      const dy = iy - jy
      const dz = iz - jz
      const distSq = dx * dx + dy * dy + dz * dz

      if (distSq < thresholdSq) {
        linePos.push(ix, iy, iz, jx, jy, jz)

        lineCol.push(
          ir,
          ig,
          ib,
          neuralCol[j * 3],
          neuralCol[j * 3 + 1],
          neuralCol[j * 3 + 2]
        )
      }
    }
  }

  const lineGeo = new BufferGeometry()
  lineGeo.setAttribute('position', new Float32BufferAttribute(linePos, 3))
  lineGeo.setAttribute('color', new Float32BufferAttribute(lineCol, 3))

  const lineMat = new LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.12,
    blending: AdditiveBlending,
    depthWrite: false
  })

  const lineSegments = new LineSegments(lineGeo, lineMat)
  sphereGroup.add(lineSegments)

  // Highlight nodes
  const highlightGeo = new BufferGeometry()
  highlightGeo.setAttribute('position', new BufferAttribute(neuralPos, 3))
  highlightGeo.setAttribute('color', new BufferAttribute(neuralCol, 3))

  const highlightMat = new PointsMaterial({
    size: 0.08,
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    blending: AdditiveBlending,
    depthWrite: false
  })

  const highlights = new Points(highlightGeo, highlightMat)
  sphereGroup.add(highlights)

  function resize() {
    const rect = host.getBoundingClientRect()
    const w = Math.max(1, Math.floor(rect.width))
    const h = Math.max(1, Math.floor(rect.height))

    camera.aspect = w / h
    camera.updateProjectionMatrix()

    renderer.setSize(w, h, false)

    const dpr = Math.min(2, window.devicePixelRatio || 1)
    renderer.setPixelRatio(dpr)
  }

  resize()

  try {
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => resize())
      resizeObserver.observe(host)
    } else {
      window.addEventListener('resize', resize, { passive: true })
    }
  } catch (_) {
    window.addEventListener('resize', resize, { passive: true })
  }

  function animate() {
    rafId = window.requestAnimationFrame(animate)
    const time = (typeof performance !== 'undefined' ? performance.now() : Date.now()) * 0.001

    stardust.rotation.y = time * 0.005

    sphereGroup.rotation.y = time * 0.1
    sphereGroup.rotation.z = time * 0.04

    const cycle = time * (Math.PI * 2 / 12)
    const scale = 1 + Math.sin(cycle) * 0.08
    sphereGroup.scale.set(scale, scale, scale)

    camera.lookAt(scene.position)

    renderer.render(scene, camera)
  }

  animate()

  cleanupFn = () => {
    try {
      if (rafId) {
        window.cancelAnimationFrame(rafId)
        rafId = 0
      }

      try {
        resizeObserver?.disconnect?.()
      } catch (_) {
        // ignore
      }
      resizeObserver = null

      try {
        window.removeEventListener('resize', resize)
      } catch (_) {
        // ignore
      }

      try {
        stardustGeo.dispose?.()
        stardustMat.dispose?.()
        denseGeo.dispose?.()
        denseMat.dispose?.()
        lineGeo.dispose?.()
        lineMat.dispose?.()
        highlightGeo.dispose?.()
        highlightMat.dispose?.()
        glowTexture.dispose?.()
        glowMaterial.dispose?.()
      } catch (_) {
        // ignore
      }

      try {
        renderer.dispose?.()
        const ext = renderer.getContext?.()?.getExtension?.('WEBGL_lose_context')
        ext?.loseContext?.()
      } catch (_) {
        // ignore
      }

      try {
        canvas.remove()
      } catch (_) {
        // ignore
      }
    } catch (_) {
      // ignore
    }

    cleanupFn = null
  }
}

onMounted(() => {
  try {
    // Keep the badge opt-in. Allow it in any mode, but only when explicitly requested.
    showDebugBadge.value = hasDebugHeroFlag()
  } catch (_) {
    // ignore
  }

  _updateAssetsState()

  // Don't block rendering: start after first paint.
  setTimeout(() => {
    mountThree()
      .catch((e) => {
        _setState('three-failed')
        _debug(`three.js failed: ${e?.message || String(e)}`)
      })
  }, 0)
})

onUnmounted(() => {
  try {
    cleanupFn?.()
  } catch (_) {
    // ignore
  }
})
</script>

<style scoped>
.hero-visual {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero-debug {
  position: fixed;
  left: 12px;
  top: 12px;
  z-index: 2147483647;
  pointer-events: none;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(10, 10, 16, 0.74);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
  font-size: 12px;
  line-height: 1.25;
  color: rgba(238, 242, 255, 0.92);
}

.hero-debug .k {
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.86;
  margin-bottom: 6px;
}

.hero-debug .v {
  opacity: 0.92;
}

.asset {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.92;
  filter: saturate(1.08);
}

.asset.sphere {
  inset: 50% auto auto 50%;
  width: min(860px, 92vw);
  height: min(860px, 92vw);
  transform: translate(-50%, -52%);
  object-fit: contain;
  opacity: 0.78;
  mix-blend-mode: screen;
  filter: blur(0px) saturate(1.15);
}

.fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(760px 520px at 20% 24%, rgba(0, 240, 255, 0.10), transparent 60%),
    radial-gradient(780px 560px at 78% 30%, rgba(157, 78, 221, 0.10), transparent 62%),
    radial-gradient(1000px 820px at 50% 86%, rgba(120, 160, 255, 0.10), transparent 60%);
}

.fallback::before {
  content: '';
  position: absolute;
  inset: -20%;
  background:
    radial-gradient(540px 420px at 45% 38%, rgba(0, 240, 255, 0.10), transparent 60%),
    radial-gradient(620px 460px at 60% 52%, rgba(157, 78, 221, 0.08), transparent 62%);
  filter: blur(0px);
  opacity: 0.55;
  transform: translate3d(0, 0, 0) scale(1);
  animation: heroPulse 7.8s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

@keyframes heroPulse {
  0% {
    opacity: 0.38;
    transform: translate3d(-1%, -1%, 0) scale(1.00);
  }
  50% {
    opacity: 0.68;
    transform: translate3d(1.2%, 0.6%, 0) scale(1.03);
  }
  100% {
    opacity: 0.38;
    transform: translate3d(-1%, -1%, 0) scale(1.00);
  }
}

.hero-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.95;
}
</style>
