<template>
  <div class="three-twin-root w-full h-full" aria-label="Three Twin">
    <div ref="container" class="three-twin w-full h-full" aria-label="Three WebGL"></div>

    <!-- Astro-GIS Phase 3+: minimal catalog hover/pick HUD (HTML overlay). -->
    <div
      v-if="catalogHudVisible"
      class="catalog-hud"
      :style="{ left: `${catalogHudX}px`, top: `${catalogHudY}px` }"
      aria-label="Catalog HUD"
    >
      <div class="catalog-hud-title">{{ catalogHudTitle }}</div>
      <div class="catalog-hud-meta">{{ catalogHudMeta }}</div>
    </div>
  </div>
</template>

<script setup>
import { markRaw, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import gsap from 'gsap'
import { useResearchStore } from '../../../stores/researchStore.js'
import { ASTRO_AGENT_ACTION_TYPES, ASTRO_GIS_LAYER_IDS, useAstroStore } from '../../../stores/astroStore.js'
import * as coordinateMath from '../../../utils/astronomy/coordinateMath.js'
import { normalizeSdssTriples } from '../../../utils/astronomy/sdssData.js'
import { disposeThreeEngine } from './threeDispose.js'
import { executeQuantumDive } from './quantumDive.js'
import { createBloomPipeline, updateBloomParams } from './threePostprocessing.js'
import { mapLayersToThreeParams } from './threeLayerMapping.js'

const emit = defineEmits(['ready'])

const props = defineProps({
  layers: { type: Array, default: () => [] },
})

const container = ref(null)

// Astro-GIS Phase 3+: catalog hover/pick tooltip.
const catalogHudVisible = ref(false)
const catalogHudX = ref(0)
const catalogHudY = ref(0)
const catalogHudTitle = ref('')
const catalogHudMeta = ref('')
const store = useResearchStore()
const astroStore = useAstroStore()

let renderer = null
let camera = null
let controls = null
let macroScene = null
let microScene = null
let activeScene = null
let composer = null
let renderPass = null
let bloomPass = null
let animationId = null
let onResize = null

let _deepSkyMesh = null
let _deepSkyUniforms = null
let _deepSkyTime = 0

// Astro-GIS Phase 2 (update_patch.md): optional texture-based skybox (equirectangular).
// Still single-canvas, single Three.js pipeline (no DOM/canvas underlays).
let _deepSkyTextureMesh = null
let _deepSkyTextureMaterial = null
let _deepSkyTextureTex = null
let _deepSkyTextureWanted = false
let _deepSkyTextureLoadErr = ''

let _catalogMesh = null
let _catalogUniforms = null
let _catalogWantedVisible = false
let _catalogLastQueryKey = ''
let _catalogLastFetchAt = 0
let _catalogAbort = null

let _catalogActiveLayerId = ''
let _catalogSources = []
let _catalogHoverIndex = -1
let _catalogPinnedIndex = -1
let _catalogPointerMoveHandler = null
let _catalogPointerDownHandler = null
const _catalogRaycaster = new THREE.Raycaster()
const _catalogMouse = new THREE.Vector2()

// Rendering/perf: hard cap for catalog Points in large FOVs.
const CATALOG_MAX_RENDER_POINTS = 1200

// Cinematic Polish engineeringization: maintain stable baselines for restore.
let _bloomBaseline = null
let _cameraBaseline = null

let macroMesh = null
let microRoot = null
let microSiMesh = null
let microOMesh = null
let microBondLines = null
let microMaterial = null
let microMaterialO = null

let _macroRedshiftTween = null
let _macroRedshiftShader = null
let _macroRedshiftMaxDepth = 52
let _macroRedshiftScale = 0

let _sdssInjected = false

let _pendingAstroAction = null

let _storyToken = 0

// Macro (SDSS) baseline should be a sky-sphere (2D celestial sphere) by default.
// This avoids the historical “spiral disk” artifact and makes radial redshift expansion
// visually/physically consistent (cosmic web rather than a cylinder).
const MACRO_SKY_RADIUS = 100
// Align the injected sky with the default camera facing direction.
const MACRO_RA_OFFSET_DEG = 180
// Keep a literal default here so baseline computations don't depend on later-in-file constants.
const MACRO_BASE_OPACITY_DEFAULT = 0.25

function _clamp01(v, fallback = 1) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : fallback
}

function _getMacroLayerState() {
  try {
    return astroStore.astroGis.value?.layers?.[ASTRO_GIS_LAYER_IDS.MACRO_SDSS] || null
  } catch (_) {
    return null
  }
}

function _computeMacroOpacityBaseline() {
  const macroL = _getMacroLayerState()
  const layerOpacity = _clamp01(macroL?.opacity, 1)
  const baseOpacity = _clamp01(macroL?.style?.baseOpacity, MACRO_BASE_OPACITY_DEFAULT)
  return _clamp01(baseOpacity * layerOpacity, MACRO_BASE_OPACITY_DEFAULT)
}

function _restoreCinematicBaseline({ camera: restoreCamera = true, bloom: restoreBloom = true, macroOpacity: restoreMacroOpacity = true } = {}) {
  // Keep name substring stable for wiring gates: restoreCinematicBaseline
  try {
    if (restoreMacroOpacity) {
      const u = macroMesh?.material?.uniforms
      const target = _computeMacroOpacityBaseline()
      if (u?.u_opacity) {
        try {
          if (gsap?.to) gsap.to(u.u_opacity, { value: target, duration: 0.6, ease: 'power2.out' })
          else u.u_opacity.value = target
        } catch (_) {
          u.u_opacity.value = target
        }
      }
    }
  } catch (_) {
    // ignore
  }

  try {
    if (restoreBloom && bloomPass && _bloomBaseline) {
      const strength = Number(_bloomBaseline.strength)
      const threshold = Number(_bloomBaseline.threshold)
      const radius = Number(_bloomBaseline.radius)
      if (Number.isFinite(strength) && Number.isFinite(threshold) && Number.isFinite(radius)) {
        gsap?.to ? gsap.to(bloomPass, { strength, threshold, radius, duration: 0.8, ease: 'power2.out' }) : Object.assign(bloomPass, { strength, threshold, radius })
      }
    }
  } catch (_) {
    // ignore
  }

  try {
    if (restoreCamera && camera && _cameraBaseline) {
      const fov = Number(_cameraBaseline.fov)
      const z = Number(_cameraBaseline.z)
      if (Number.isFinite(fov)) {
        gsap?.to
          ? gsap.to(camera, {
            fov,
            duration: 0.8,
            ease: 'power2.out',
            onUpdate: () => {
              try {
                camera.updateProjectionMatrix?.()
              } catch (_) {
                // ignore
              }
            },
          })
          : (camera.fov = fov)
      }
      if (camera?.position && Number.isFinite(z)) {
        gsap?.to ? gsap.to(camera.position, { z, duration: 0.8, ease: 'power2.out' }) : (camera.position.z = z)
      }
    }
  } catch (_) {
    // ignore
  }

  // update_patch.md: ensure background yields/recovers deterministically across interrupts.
  try {
    if (_deepSkyUniforms?.u_dim) _deepSkyUniforms.u_dim.value = 1.0
  } catch (_) {
    // ignore
  }

  // Keep texture-skybox opacity in sync with dim restore.
  try {
    _syncDeepSkyTextureOpacity()
  } catch (_) {
    // ignore
  }
}

function _sleep(ms) {
  const t = Number(ms)
  const delay = Number.isFinite(t) ? Math.max(0, Math.floor(t)) : 0
  return new Promise((resolve) => setTimeout(resolve, delay))
}

function _cancelStoryFlow() {
  _storyToken += 1
  try {
    _stopGottaTransient()
  } catch (_) {
    // ignore
  }
  try {
    _stopModalInpaint()
  } catch (_) {
    // ignore
  }
  try {
    _stopCsstDecomposition({ restoreCamera: true })
  } catch (_) {
    // ignore
  }
  try {
    _setMacroRedshiftScale(0)
  } catch (_) {
    // ignore
  }

  // Phase 2.7: ensure cinematic state does not drift across STOP.
  try {
    _restoreCinematicBaseline({ camera: true, bloom: true, macroOpacity: true })
  } catch (_) {
    // ignore
  }
}

function _tryRunAstroAction(action) {
  if (!action || typeof action !== 'object') return false
  const type = String(action?.type || '').trim()

  if (type === ASTRO_AGENT_ACTION_TYPES.STOP_ONEASTRO_STORY_FLOW) {
    _cancelStoryFlow()
    return true
  }

  // Stop should work regardless of the current scale.
  if (type === ASTRO_AGENT_ACTION_TYPES.STOP_MODAL_INPAINT) {
    try {
      _stopModalInpaint()
    } catch (_) {
      // ignore
    }
    return true
  }

  if (type === ASTRO_AGENT_ACTION_TYPES.STOP_CSST_DECOMPOSITION) {
    try {
      _stopCsstDecomposition({ restoreCamera: true })
    } catch (_) {
      // ignore
    }
    return true
  }

  // Stage 2: run only in macro scene.
  const scale = String(store.currentScale.value || '').trim().toLowerCase()
  if (scale !== 'macro') return false

  if (type === ASTRO_AGENT_ACTION_TYPES.EXECUTE_ONEASTRO_STORY_FLOW) {
    if (!macroScene || !renderer || !camera) return false
    void _executeOneAstroStoryFlow(action?.payload || null)
    return true
  }

  if (type === ASTRO_AGENT_ACTION_TYPES.EXECUTE_REDSHIFT_PREDICTION) {
    if (!macroMesh) return false
    void _executeRedshiftBurst(action?.payload || null)
    return true
  }

  if (type === ASTRO_AGENT_ACTION_TYPES.DECOMPOSE_CSST_GALAXY) {
    if (!macroScene || !renderer || !camera) return false
    _startCsstDecomposition(action?.payload || null)
    return true
  }

  if (type === ASTRO_AGENT_ACTION_TYPES.START_MODAL_INPAINT) {
    if (!_inpaintMesh || !_inpaintUniforms || !renderer || !camera) return false
    _startModalInpaint(action?.payload || null)
    return true
  }

  if (type === ASTRO_AGENT_ACTION_TYPES.CAPTURE_TRANSIENT_EVENT) {
    if (!macroScene || !renderer || !camera) return false
    void _captureTransientEvent(action?.payload || null)
    return true
  }

  return false
}

async function _executeOneAstroStoryFlow(payload = null) {
  const token = (_storyToken += 1)
  const canceled = () => token !== _storyToken

  // Enforce narrative exclusivity: start from a clean macro overlay state.
  try {
    _stopGottaTransient()
  } catch (_) {
    // ignore
  }
  try {
    _stopModalInpaint()
  } catch (_) {
    // ignore
  }
  try {
    _stopCsstDecomposition({ restoreCamera: false })
  } catch (_) {
    // ignore
  }
  try {
    _setMacroRedshiftScale(0)
  } catch (_) {
    // ignore
  }

  try {
    astroStore.setGenerating(true)
  } catch (_) {
    // ignore
  }

  // Act 1: CSST decomposition (close-up)
  try {
    _startCsstDecomposition(payload?.csst || null)
  } catch (_) {
    // ignore
  }
  await _sleep(1700)
  if (canceled()) return

  // Clear CSST before going wide.
  try {
    _stopCsstDecomposition({ restoreCamera: false })
  } catch (_) {
    // ignore
  }
  await _sleep(350)
  if (canceled()) return

  // Act 2: redshift radial expansion (go wide)
  try {
    await _executeRedshiftBurst(payload?.redshift || { maxDepth: 52 })
  } catch (_) {
    // ignore
  }
  if (canceled()) return

  // Act 3: GOTTA transient capture (spline dive)
  try {
    await _captureTransientEvent(payload?.gotta || null)
  } catch (_) {
    // ignore
  }
  if (canceled()) return

  // Act 4: Inpaint, anchored at the GOTTA target.
  try {
    const pos = _gottaLastTargetPos ? { x: _gottaLastTargetPos.x, y: _gottaLastTargetPos.y, z: _gottaLastTargetPos.z } : null
    _startModalInpaint(pos ? { position: pos } : (payload?.inpaint || null))
  } catch (_) {
    // ignore
  }

  try {
    astroStore.setGenerating(false)
  } catch (_) {
    // ignore
  }
}

function _flushPendingAstroAction() {
  if (!_pendingAstroAction) return
  if (_tryRunAstroAction(_pendingAstroAction)) _pendingAstroAction = null
}

let _inpaintMesh = null
let _inpaintUniforms = null
let _inpaintActive = false
let _inpaintClickHandler = null
let _inpaintRadiusTween = null
let _inpaintTime = 0
const _inpaintRaycaster = new THREE.Raycaster()
const _inpaintMouse = new THREE.Vector2()

let _csstGroup = null

function _formatCatalogHudMeta(source) {
  if (!source || typeof source !== 'object') return ''
  const mag = Number(source?.mag_v)
  const magStr = Number.isFinite(mag) ? `V=${mag.toFixed(2)}` : ''
  const otype = String(source?.otype || '').trim()
  const ra = Number(source?.ra_deg)
  const dec = Number(source?.dec_deg)
  const radec = (Number.isFinite(ra) && Number.isFinite(dec)) ? `RA=${ra.toFixed(2)}°, Dec=${dec.toFixed(2)}°` : ''
  return [magStr, otype, radec].filter(Boolean).join(' · ')
}

function _hideCatalogHud() {
  catalogHudVisible.value = false
  catalogHudTitle.value = ''
  catalogHudMeta.value = ''
  _catalogHoverIndex = -1
}

function _showCatalogHudAt(index, xPx, yPx) {
  const i = Number(index)
  if (!Number.isFinite(i) || i < 0 || i >= _catalogSources.length) return _hideCatalogHud()
  const s = _catalogSources[i]
  const name = String(s?.name || s?.id || 'Catalog Object').trim() || 'Catalog Object'
  catalogHudTitle.value = name
  catalogHudMeta.value = _formatCatalogHudMeta(s)
  catalogHudX.value = Math.max(0, Math.floor(Number(xPx) || 0))
  catalogHudY.value = Math.max(0, Math.floor(Number(yPx) || 0))
  catalogHudVisible.value = true
}

function sampleCatalogSources(sources, maxPoints = CATALOG_MAX_RENDER_POINTS, seedKey = '') {
  const list = Array.isArray(sources) ? sources : []
  const cap = Math.max(1, Math.min(2000, Math.floor(Number(maxPoints) || CATALOG_MAX_RENDER_POINTS)))
  if (list.length <= cap) return list

  // Deterministic sampling: hash ids with a seed so the selected set is stable
  // for the same query (avoids flicker while orbiting).
  const seed = _hashSeed(`catalog-sample:${seedKey}`)
  const keyOf = (s) => String(s?.id || s?.name || '').trim() || JSON.stringify(s)
  const score = (k) => {
    // 32-bit FNV-like mix with seed.
    const t = `${seed}|${k}`
    let h = 2166136261
    for (let i = 0; i < t.length; i += 1) {
      h ^= t.charCodeAt(i)
      h = Math.imul(h, 16777619)
    }
    return h >>> 0
  }

  const ranked = list.map((s) => ({ s, h: score(keyOf(s)) }))
  ranked.sort((a, b) => a.h - b.h)
  return ranked.slice(0, cap).map((x) => x.s)
}

function _abortCatalogFetch() {
  if (!_catalogAbort) return
  try {
    _catalogAbort.abort()
  } catch (_) {
    // ignore
  }
  _catalogAbort = null
}

function _ensureCatalogLayer() {
  if (_catalogMesh || !macroScene) return
  if (!THREE) return

  try {
    const geom = new THREE.BufferGeometry()
    geom.setAttribute('position', new THREE.Float32BufferAttribute([], 3))
    geom.setAttribute('aMag', new THREE.Float32BufferAttribute([], 1))

    _catalogUniforms = {
      u_opacity: { value: 1.0 },
    }

    const mat = new THREE.ShaderMaterial({
      uniforms: _catalogUniforms,
      transparent: true,
      depthTest: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: `
        attribute float aMag;
        uniform float u_opacity;
        varying float vAlpha;
        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          // Map V-mag into a readable size range.
          float mag = clamp(aMag, -1.0, 22.0);
          float size = mix(6.0, 1.6, clamp((mag - 2.0) / 16.0, 0.0, 1.0));
          gl_PointSize = size;
          vAlpha = clamp(u_opacity, 0.0, 1.0);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        varying float vAlpha;
        void main() {
          vec2 p = gl_PointCoord - vec2(0.5);
          float r = length(p);
          float a = smoothstep(0.5, 0.0, r);
          if (a < 0.02) discard;
          vec3 col = vec3(0.35, 0.85, 1.0);
          float alpha = a * vAlpha;
          gl_FragColor = vec4(col * alpha, alpha);
        }
      `,
    })

    _catalogMesh = markRaw(new THREE.Points(geom, mat))
    _catalogMesh.frustumCulled = false
    _catalogMesh.visible = false
    _catalogMesh.renderOrder = 990
    macroScene.add(_catalogMesh)
  } catch (_) {
    _catalogMesh = null
    _catalogUniforms = null
  }
}

function _unbindCatalogPointerHandlers() {
  if (!_catalogPointerMoveHandler || !renderer?.domElement) {
    _catalogPointerMoveHandler = null
    _catalogPointerDownHandler = null
    return
  }
  try {
    renderer.domElement.removeEventListener('pointermove', _catalogPointerMoveHandler)
  } catch (_) {
    // ignore
  }
  try {
    if (_catalogPointerDownHandler) renderer.domElement.removeEventListener('pointerdown', _catalogPointerDownHandler)
  } catch (_) {
    // ignore
  }
  _catalogPointerMoveHandler = null
  _catalogPointerDownHandler = null
}

function _bindCatalogPointerHandlers() {
  if (!renderer?.domElement || !camera) return
  if (_catalogPointerMoveHandler) return

  _catalogPointerMoveHandler = (ev) => {
    try {
      if (!_catalogMesh?.visible || !_catalogSources?.length) {
        if (_catalogPinnedIndex < 0) _hideCatalogHud()
        return
      }

      const rect = renderer.domElement.getBoundingClientRect()
      const w = Math.max(1, rect.width)
      const h = Math.max(1, rect.height)
      const x = ((ev.clientX - rect.left) / w) * 2 - 1
      const y = -(((ev.clientY - rect.top) / h) * 2 - 1)
      _catalogMouse.set(x, y)

      _catalogRaycaster.setFromCamera(_catalogMouse, camera)
      // Threshold is in world units for Points; keep small (sky-sphere radius ~100).
      _catalogRaycaster.params.Points = _catalogRaycaster.params.Points || {}
      _catalogRaycaster.params.Points.threshold = 0.9

      const hits = _catalogRaycaster.intersectObject(_catalogMesh, false)
      const hit = hits && hits.length ? hits[0] : null
      const idx = Number(hit?.index)
      if (!Number.isFinite(idx) || idx < 0 || idx >= _catalogSources.length) {
        _catalogHoverIndex = -1
        if (_catalogPinnedIndex < 0) _hideCatalogHud()
        return
      }

      _catalogHoverIndex = idx
      if (_catalogPinnedIndex < 0) {
        _showCatalogHudAt(idx, (ev.clientX - rect.left) + 14, (ev.clientY - rect.top) + 14)
      }
    } catch (_) {
      // ignore
    }
  }

  _catalogPointerDownHandler = (ev) => {
    try {
      if (!_catalogMesh?.visible || !_catalogSources?.length) return
      const rect = renderer.domElement.getBoundingClientRect()
      const w = Math.max(1, rect.width)
      const h = Math.max(1, rect.height)
      const x = ((ev.clientX - rect.left) / w) * 2 - 1
      const y = -(((ev.clientY - rect.top) / h) * 2 - 1)
      _catalogMouse.set(x, y)
      _catalogRaycaster.setFromCamera(_catalogMouse, camera)
      _catalogRaycaster.params.Points = _catalogRaycaster.params.Points || {}
      _catalogRaycaster.params.Points.threshold = 0.9

      const hits = _catalogRaycaster.intersectObject(_catalogMesh, false)
      const hit = hits && hits.length ? hits[0] : null
      const idx = Number(hit?.index)
      if (!Number.isFinite(idx) || idx < 0 || idx >= _catalogSources.length) {
        _catalogPinnedIndex = -1
        _hideCatalogHud()
        return
      }

      _catalogPinnedIndex = idx
      _showCatalogHudAt(idx, (ev.clientX - rect.left) + 14, (ev.clientY - rect.top) + 14)
    } catch (_) {
      // ignore
    }
  }

  try {
    renderer.domElement.addEventListener('pointermove', _catalogPointerMoveHandler, { passive: true })
  } catch (_) {
    // ignore
  }
  try {
    renderer.domElement.addEventListener('pointerdown', _catalogPointerDownHandler, { passive: true })
  } catch (_) {
    // ignore
  }
}

function _updateCatalogSources(sources) {
  if (!_catalogMesh) _ensureCatalogLayer()
  if (!_catalogMesh?.geometry) return

  const list = sampleCatalogSources(Array.isArray(sources) ? sources : [], CATALOG_MAX_RENDER_POINTS, _catalogLastQueryKey)
  const n = Math.max(0, Math.min(2000, list.length))
  const radius = MACRO_SKY_RADIUS + 0.8

  _catalogSources = list
  _catalogHoverIndex = -1
  _catalogPinnedIndex = -1
  _hideCatalogHud()

  const pos = new Float32Array(n * 3)
  const mags = new Float32Array(n)

  for (let i = 0; i < n; i += 1) {
    const s = list[i] || null
    const ra = Number(s?.ra_deg)
    const dec = Number(s?.dec_deg)
    const mag = Number(s?.mag_v)
    if (!Number.isFinite(ra) || !Number.isFinite(dec)) continue

    const dir = coordinateMath.raDecToUnitVector(ra + MACRO_RA_OFFSET_DEG, dec)
    pos[i * 3] = dir.x * radius
    pos[i * 3 + 1] = dir.z * radius
    pos[i * 3 + 2] = dir.y * radius
    mags[i] = Number.isFinite(mag) ? mag : 12.0
  }

  try {
    _catalogMesh.geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    _catalogMesh.geometry.setAttribute('aMag', new THREE.BufferAttribute(mags, 1))
    _catalogMesh.geometry.setDrawRange(0, n)
    _catalogMesh.geometry.computeBoundingSphere?.()
  } catch (_) {
    // ignore
  }
}

function _catalogQueryKey({ raDeg, decDeg, radiusDeg, maxRows }) {
  // Quantize to avoid refetching on tiny camera jitter.
  const q = (x, step) => Math.round(Number(x) / step) * step
  const raQ = q(raDeg, 0.5)
  const decQ = q(decDeg, 0.5)
  const rQ = q(radiusDeg, 0.5)
  const mQ = Math.max(1, Math.min(2000, Math.floor(Number(maxRows) || 600)))
  return `${raQ}|${decQ}|${rQ}|${mQ}`
}

async function _maybeFetchCatalog(layer, view, nowMs) {
  if (!_catalogWantedVisible) return
  if (typeof fetch !== 'function') return

  const provider = String(layer?.source?.provider || '').trim().toLowerCase()
  const defaultEndpoint = provider === 'vizier' ? '/api/astro-gis/catalog/vizier' : '/api/astro-gis/catalog/simbad'
  const endpoint = String(layer?.source?.endpoint || defaultEndpoint).trim() || defaultEndpoint
  const maxRows = Math.max(1, Math.min(2000, Math.floor(Number(layer?.style?.maxRows) || 600)))
  const radiusDeg = Math.max(0.5, Math.min(45, Number(view?.fovDeg || 60) * 0.55))
  const key = _catalogQueryKey({ raDeg: view.raDeg, decDeg: view.decDeg, radiusDeg, maxRows })
  if (key === _catalogLastQueryKey) return

  // Rate limit.
  if (nowMs - _catalogLastFetchAt < 450) return
  _catalogLastFetchAt = nowMs

  _abortCatalogFetch()
  _catalogAbort = new AbortController()

  let url = `${endpoint}?ra=${encodeURIComponent(view.raDeg)}&dec=${encodeURIComponent(view.decDeg)}&radius=${encodeURIComponent(radiusDeg)}&maxRows=${encodeURIComponent(maxRows)}`
  try {
    if (provider === 'vizier') {
      const catalog = String(layer?.style?.catalog || '').trim()
      if (catalog) url += `&catalog=${encodeURIComponent(catalog)}`
    }
  } catch (_) {
    // ignore
  }

  let data = null
  try {
    const res = await fetch(url, { cache: 'no-store', signal: _catalogAbort.signal })
    if (!res?.ok) return
    data = await res.json()
  } catch (_) {
    return
  } finally {
    _catalogAbort = null
  }

  const sources = Array.isArray(data?.sources) ? data.sources : []
  _catalogLastQueryKey = key
  _updateCatalogSources(sources)
}

function _applyAstroGisLayerState(astroGis) {
  const layers = astroGis?.layers || null
  if (!layers || typeof layers !== 'object') return

  const macroL = layers[ASTRO_GIS_LAYER_IDS.MACRO_SDSS] || null
  const csstL = layers[ASTRO_GIS_LAYER_IDS.DEMO_CSST] || null
  const gottaL = layers[ASTRO_GIS_LAYER_IDS.DEMO_GOTTA] || null
  const inpaintL = layers[ASTRO_GIS_LAYER_IDS.DEMO_INPAINT] || null
  const hipsL = layers[ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND] || null
  const catalogSimbadL = layers[ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD] || null
  const catalogVizierL = layers[ASTRO_GIS_LAYER_IDS.CATALOG_VIZIER] || null

  if (macroMesh) {
    try {
      macroMesh.visible = macroL ? !!macroL.visible : true
    } catch (_) {
      // ignore
    }
    try {
      const u = macroMesh?.material?.uniforms || _macroRedshiftShader?.uniforms
      const op = macroL ? Number(macroL.opacity) : 1
      const clamped = Number.isFinite(op) ? Math.max(0, Math.min(1, op)) : 1
      const baseOpacityRaw = Number(macroL?.style?.baseOpacity)
      const baseOpacity = Number.isFinite(baseOpacityRaw) ? Math.max(0, Math.min(1, baseOpacityRaw)) : MACRO_BASE_OPACITY
      if (u?.u_opacity) u.u_opacity.value = baseOpacity * clamped
      if (u?.u_size) {
        const ps = Number(macroL?.style?.pointSize)
        if (Number.isFinite(ps)) u.u_size.value = Math.max(1, Math.min(250, ps))
      }
      // Heatmap palette parameters (Near/Mid/Far) can be overridden via layer store.
      const pal = macroL?.style?.palette
      const near = Array.isArray(pal?.near) ? pal.near : null
      const mid = Array.isArray(pal?.mid) ? pal.mid : null
      const far = Array.isArray(pal?.far) ? pal.far : null
      if (u?.u_colorNear?.value && near && near.length >= 3) u.u_colorNear.value.set(Number(near[0]) || 0, Number(near[1]) || 0, Number(near[2]) || 0)
      if (u?.u_colorMid?.value && mid && mid.length >= 3) u.u_colorMid.value.set(Number(mid[0]) || 0, Number(mid[1]) || 0, Number(mid[2]) || 0)
      if (u?.u_colorFar?.value && far && far.length >= 3) u.u_colorFar.value.set(Number(far[0]) || 0, Number(far[1]) || 0, Number(far[2]) || 0)
    } catch (_) {
      // ignore
    }
  }

  if (_csstGroup) {
    try {
      _csstGroup.visible = csstL ? !!csstL.visible : true
    } catch (_) {
      // ignore
    }
  }
  try {
    const op = csstL ? Number(csstL.opacity) : 1
    const clamped = Number.isFinite(op) ? Math.max(0, Math.min(1, op)) : 1
    if (Array.isArray(_csstPlanes)) {
      for (const p of _csstPlanes) {
        const u = p?.material?.uniforms
        if (u?.u_opacity) u.u_opacity.value = clamped
      }
    }
  } catch (_) {
    // ignore
  }

  if (_gottaGroup) {
    try {
      _gottaGroup.visible = gottaL ? !!gottaL.visible : true
    } catch (_) {
      // ignore
    }
    try {
      const op = gottaL ? Number(gottaL.opacity) : 1
      const clamped = Number.isFinite(op) ? Math.max(0, Math.min(1, op)) : 1
      _gottaGroup.traverse?.((o) => {
        const m = o?.material
        if (m && typeof m === 'object' && 'opacity' in m) {
          m.transparent = true
          const ud = (m.userData && typeof m.userData === 'object') ? m.userData : (m.userData = {})
          if (ud.__astroBaseOpacity === undefined) ud.__astroBaseOpacity = Number(m.opacity)
          const base = Number(ud.__astroBaseOpacity)
          const baseOp = Number.isFinite(base) ? base : 1
          m.opacity = Math.max(0, Math.min(1, baseOp * clamped))
          m.needsUpdate = true
        }
      })
    } catch (_) {
      // ignore
    }
  }

  if (_inpaintMesh && _inpaintUniforms) {
    try {
      const visible = inpaintL ? !!inpaintL.visible : true
      _inpaintMesh.visible = !!_inpaintActive && visible
    } catch (_) {
      // ignore
    }
    try {
      const op = inpaintL ? Number(inpaintL.opacity) : 1
      const clamped = Number.isFinite(op) ? Math.max(0, Math.min(1, op)) : 1
      if (_inpaintUniforms.u_layer_opacity) _inpaintUniforms.u_layer_opacity.value = clamped
    } catch (_) {
      // ignore
    }
  }

  // Astro-GIS Phase 2: Deep Sky Background (single-canvas native skybox).
  try {
    const wanted = hipsL ? !!hipsL.visible : false
    if (wanted) _ensureDeepSkyBackground()

    const presetRaw = String(hipsL?.style?.preset || 'procedural').trim().toLowerCase()
    const preset = (presetRaw === 'texture') ? 'texture' : ((presetRaw === 'black' || presetRaw === 'off') ? 'black' : 'procedural')

    // Two-gear strategy (update_patch.md): procedural/black baseline, optional texture preset.
    _deepSkyTextureWanted = wanted && (preset === 'texture')
    if (preset === 'texture' && wanted) {
      const texturePath = String(hipsL?.style?.texturePath || '/assets/eso_milkyway_8k.jpg').trim() || '/assets/eso_milkyway_8k.jpg'
      _ensureDeepSkyTextureSkybox(texturePath)
    }

    const texReady = !!_deepSkyTextureMesh
    const showTexture = wanted && (preset === 'texture') && texReady
    const showProcedural = wanted && (!showTexture)
    if (_deepSkyMesh) _deepSkyMesh.visible = showProcedural
    if (_deepSkyTextureMesh) _deepSkyTextureMesh.visible = showTexture

    const op = hipsL ? Number(hipsL.opacity) : 1
    const clamped = Number.isFinite(op) ? Math.max(0, Math.min(1, op)) : 1

    const starDensityRaw = Number(hipsL?.style?.starDensity)
    const starDensity = Number.isFinite(starDensityRaw) ? Math.max(0, Math.min(1, starDensityRaw)) : 0.65
    const milkyWay = hipsL?.style?.milkyWay === undefined ? true : !!hipsL.style.milkyWay

    const textureOpacityRaw = Number(hipsL?.style?.textureOpacity)
    const textureOpacity = Number.isFinite(textureOpacityRaw) ? Math.max(0, Math.min(1, textureOpacityRaw)) : 0.85

    if (_deepSkyUniforms?.u_opacity) _deepSkyUniforms.u_opacity.value = clamped

    // UX: if preset=texture but the texture is still loading (or failed), keep procedural
    // stars visible as a fallback. Only turn procedural off when black is explicitly
    // requested or when the texture is actually being shown.
    const proceduralOff = (preset === 'black' || showTexture)
    if (_deepSkyUniforms?.u_starDensity) _deepSkyUniforms.u_starDensity.value = proceduralOff ? 0 : starDensity
    if (_deepSkyUniforms?.u_milkyWay) _deepSkyUniforms.u_milkyWay.value = proceduralOff ? 0 : (milkyWay ? 1 : 0)

    if (_deepSkyTextureMaterial) {
      const ud = (_deepSkyTextureMaterial.userData && typeof _deepSkyTextureMaterial.userData === 'object') ? _deepSkyTextureMaterial.userData : (_deepSkyTextureMaterial.userData = {})
      ud.__astroBaseOpacity = textureOpacity
      ud.__astroLayerOpacity = clamped
      _syncDeepSkyTextureOpacity()
    }
  } catch (_) {
    // ignore
  }

  // Phase 3+: catalog overlay (SIMBAD/VizieR) (best-effort; backend defaults to offline fixtures).
  try {
    const activeCatalogL = (catalogVizierL && catalogVizierL.visible) ? catalogVizierL : ((catalogSimbadL && catalogSimbadL.visible) ? catalogSimbadL : null)
    const wanted = !!activeCatalogL
    _catalogWantedVisible = wanted

    const activeId = String(activeCatalogL?.id || '').trim()
    if (activeId && activeId !== _catalogActiveLayerId) {
      _catalogActiveLayerId = activeId
      _catalogLastQueryKey = ''
      _catalogLastFetchAt = 0
      _abortCatalogFetch()
      _catalogSources = []
      _catalogHoverIndex = -1
      _catalogPinnedIndex = -1
      _hideCatalogHud()
    }

    if (wanted) {
      _ensureCatalogLayer()
      if (_catalogMesh) _catalogMesh.visible = true
    } else {
      if (_catalogMesh) _catalogMesh.visible = false
      _abortCatalogFetch()
      _catalogActiveLayerId = ''
      _catalogSources = []
      _catalogHoverIndex = -1
      _catalogPinnedIndex = -1
      _hideCatalogHud()
    }

    const op = activeCatalogL ? Number(activeCatalogL.opacity) : 1
    const clamped = Number.isFinite(op) ? Math.max(0, Math.min(1, op)) : 1
    if (_catalogUniforms?.u_opacity) _catalogUniforms.u_opacity.value = 0.9 * clamped
  } catch (_) {
    // ignore
  }
}

function _computeMacroViewRaDecFov() {
  if (!camera) return null
  try {
    const d = new THREE.Vector3()
    camera.getWorldDirection(d)
    const astroDir = { x: d.x, y: d.z, z: d.y }
    const { raDeg, decDeg } = coordinateMath.unitVectorToRaDec(astroDir)
    const raAligned = coordinateMath.normalizeAngle0To360(raDeg - MACRO_RA_OFFSET_DEG)
    const fovDeg = Number(camera.fov)
    return {
      raDeg: raAligned,
      decDeg: Number(decDeg) || 0,
      fovDeg: Number.isFinite(fovDeg) ? fovDeg : 60,
    }
  } catch (_) {
    return null
  }
}

function _ensureDeepSkyBackground() {
  if (_deepSkyMesh || !macroScene) return
  const geo = new THREE.SphereGeometry(5000, 48, 32)
  const uniforms = {
    u_time: { value: 0 },
    u_opacity: { value: 1 },
    u_dim: { value: 1 },
    u_starDensity: { value: 0.65 },
    u_milkyWay: { value: 1 },
    u_seed: { value: _hashSeed('deep-sky-v1') },
  }

  const mat = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      precision highp float;
      varying vec3 vDir;
      uniform float u_time;
      uniform float u_opacity;
      uniform float u_dim;
      uniform float u_starDensity;
      uniform float u_milkyWay;
      uniform float u_seed;

      float hash12(vec2 p) {
        float h = dot(p, vec2(127.1, 311.7)) + u_seed * 0.00013;
        return fract(sin(h) * 43758.5453123);
      }

      vec3 deepBase(vec2 uv) {
        // Slight gradient: darker zenith, subtle blue lift near horizon.
        float y = uv.y;
        return mix(vec3(0.004, 0.006, 0.012), vec3(0.010, 0.014, 0.024), smoothstep(0.0, 1.0, y));
      }

      float starLayer(vec2 uv, float scale, float density, float timeJitter) {
        vec2 p = uv * scale;
        vec2 cell = floor(p);
        vec2 f = fract(p) - 0.5;
        float r = length(f);
        float rnd = hash12(cell);

        // Density controls the threshold; larger density means more stars.
        float threshold = 1.0 - clamp(density, 0.0, 1.0) * 0.18;
        float on = step(threshold, rnd);

        float tw = 0.75 + 0.25 * sin(u_time * 2.0 + rnd * 6.2831 + timeJitter);
        float size = mix(0.10, 0.02, rnd);
        float core = smoothstep(size, 0.0, r);
        return on * core * tw;
      }

      void main() {
        // Convert direction to equirectangular uv.
        vec3 d = normalize(vDir);
        float lon = atan(d.z, d.x);
        float lat = asin(clamp(d.y, -1.0, 1.0));
        vec2 uv = vec2(lon / (6.28318530718) + 0.5, lat / 3.14159265359 + 0.5);

        vec3 col = deepBase(uv);

        float density = clamp(u_starDensity, 0.0, 1.0);
        float s1 = starLayer(uv, 900.0, density, 1.0);
        float s2 = starLayer(uv, 1800.0, density * 0.8, 2.3) * 0.8;
        float s3 = starLayer(uv, 3600.0, density * 0.6, 3.7) * 0.6;
        float stars = clamp(s1 + s2 + s3, 0.0, 1.5);

        // Milky-way-ish band: a soft diagonal haze.
        float band = 0.0;
        if (u_milkyWay > 0.5) {
          float curve = 0.25 * sin(lon * 0.75) + 0.10 * sin(lon * 2.0);
          float dist = abs(lat - curve);
          band = exp(-dist * dist * 18.0);
        }

        vec3 starCol = mix(vec3(0.85, 0.90, 1.00), vec3(1.00, 0.92, 0.85), smoothstep(0.3, 1.0, stars));
        col += starCol * stars * 0.55;
        col += vec3(0.08, 0.10, 0.14) * band * 0.65;

        col = clamp(col, 0.0, 1.0);
        gl_FragColor = vec4(col, clamp(u_opacity * u_dim, 0.0, 1.0));
      }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    side: THREE.BackSide,
  })
  mat.toneMapped = false

  const mesh = new THREE.Mesh(geo, mat)
  mesh.frustumCulled = false
  mesh.renderOrder = -1000
  mesh.visible = false
  macroScene.add(mesh)
  _deepSkyMesh = mesh
  _deepSkyUniforms = uniforms
}

function _syncDeepSkyTextureOpacity() {
  const mat = _deepSkyTextureMaterial
  if (!mat) return
  const ud = (mat.userData && typeof mat.userData === 'object') ? mat.userData : (mat.userData = {})
  const baseOpacity = _clamp01(ud.__astroBaseOpacity, 0.85)
  const layerOpacity = _clamp01(ud.__astroLayerOpacity, 1.0)
  const dim = _clamp01(_deepSkyUniforms?.u_dim?.value, 1.0)
  // Allow low-opacity tuning; do not clamp to a high minimum.
  mat.opacity = _clamp01(baseOpacity * layerOpacity * dim, 1.0)
  mat.needsUpdate = true
}

function _ensureDeepSkyTextureSkybox(texturePath = '/assets/eso_milkyway_8k.jpg') {
  if (_deepSkyTextureMesh || !macroScene) return

  // update_patch.md: Native texture skybox uses an inside-out sphere.
  const textureLoader = new THREE.TextureLoader()
  textureLoader.load(
    String(texturePath || '/assets/eso_milkyway_8k.jpg'),
    (texture) => {
      // If the component was unmounted while the texture was inflight,
      // bail out safely (avoid adding to a null scene).
      if (!macroScene) {
        try { texture?.dispose?.() } catch (_) { /* ignore */ }
        return
      }
      try {
        // NOTE: When using a texture as a regular `map` on SphereGeometry,
        // do NOT switch to EquirectangularReflectionMapping (that's for env maps).
        texture.colorSpace = THREE.SRGBColorSpace
        texture.generateMipmaps = true
        texture.minFilter = THREE.LinearMipmapLinearFilter
      } catch (_) {
        // ignore
      }

      const sphereGeo = new THREE.SphereGeometry(8000, 64, 64)

      const sphereMat = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        opacity: 0.8,
        // update_patch.md (upgrade): avoid over-darkening; keep a mild grey tint.
        color: 0x888888,
        side: THREE.BackSide,
        // update_patch.md: strict depth isolation.
        depthWrite: false,
        depthTest: false,
      })
      sphereMat.toneMapped = false

      const skyboxMesh = new THREE.Mesh(sphereGeo, sphereMat)
      skyboxMesh.frustumCulled = false
      skyboxMesh.visible = false
      // update_patch.md: force render pipeline to the bottom.
      skyboxMesh.renderOrder = -999

      macroScene.add(skyboxMesh)

      _deepSkyTextureMesh = skyboxMesh
      _deepSkyTextureMaterial = sphereMat
      _deepSkyTextureTex = texture

      try {
        const ud = (sphereMat.userData && typeof sphereMat.userData === 'object') ? sphereMat.userData : (sphereMat.userData = {})
        if (ud.__astroBaseOpacity === undefined) ud.__astroBaseOpacity = 0.8
        if (ud.__astroLayerOpacity === undefined) ud.__astroLayerOpacity = 1.0
      } catch (_) {
        // ignore
      }

      try {
        _syncDeepSkyTextureOpacity()
      } catch (_) {
        // ignore
      }

      // Critical: texture is loaded asynchronously. Re-apply layer state so
      // `showTexture` flips on immediately without requiring a UI change.
      try {
        _applyAstroGisLayerState(astroStore.astroGis.value)
      } catch (_) {
        // ignore
      }
    },
    undefined,
    (err) => {
      _deepSkyTextureLoadErr = String(err?.message || err || 'texture load error')
      try {
        if (import.meta?.env?.DEV) {
          console.warn('[astro-gis][deep-sky] texture skybox load failed:', texturePath, _deepSkyTextureLoadErr)
        }
      } catch (_) {
        // ignore
      }
    }
  )
}
let _csstPlanes = null
let _csstActive = false
let _csstTimeline = null
let _csstTargetPos = null
let _csstPrevCamPos = null
let _csstPrevTarget = null
let _csstTextures = []

let _gottaGroup = null
let _gottaPulseTween = null
let _gottaMarkerTexture = null
let _gottaActive = false
let _gottaDiveTween = null
let _gottaLastTargetPos = null

const MICRO_MAX_INSTANCES = 12000

// update_patch.md (Cinematic Polish): macro cosmic web readability is dominated by
// the “overlap trick” (big halo + low opacity) and a heatmap palette.
const MACRO_BASE_OPACITY = 0.25
const MACRO_BASE_POINT_SIZE = 80.0

function _hashSeed(s) {
  const t = String(s || 'sio2')
  let h = 2166136261
  for (let i = 0; i < t.length; i += 1) {
    h ^= t.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return (h >>> 0) || 1
}

function _mulberry32(seed) {
  let a = (Number(seed) >>> 0) || 1
  return () => {
    a |= 0
    a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

let _macroSpinTween = null

function _buildMacroScene(scene) {
  // Macro cosmic web renderer.
  // Phase 2.6 (update_patch.md): use THREE.Points with a soft-particle shader so
  // additive blending self-fuses into a readable cosmic web (not independent "candy spheres").
  const count = 100000
  const geometry = new THREE.BufferGeometry()

  const positions = new Float32Array(count * 3)
  const redshift = new Float32Array(count)

  // Stage 2 Demo 1 (volumetric burst): ShaderMaterial to fully own the pipeline.
  // This guarantees `aRedshift` is actually bound and used.
  const material = new THREE.ShaderMaterial({
    uniforms: {
      u_redshift_scale: { value: 0.0 },
      u_max_depth: { value: Number(_macroRedshiftMaxDepth) || 52.0 },
      // Additive blending must start dark; the halo shader provides perceived brightness.
      u_opacity: { value: 0.25 },
      u_size: { value: 80.0 },
      // Cinematic polish: 3-stop heatmap palette (Near/Mid/Far).
      u_colorNear: { value: new THREE.Vector3(0.02, 0.40, 0.80) },
      u_colorMid: { value: new THREE.Vector3(0.60, 0.10, 0.70) },
      u_colorFar: { value: new THREE.Vector3(1.00, 0.40, 0.05) },
    },
    vertexShader: [
      'attribute float aRedshift;',
      'uniform float u_redshift_scale;',
      'uniform float u_max_depth;',
      'uniform float u_size;',
      'varying float vRedshift;',
      'varying vec3 vWorldPos;',
      'void main() {',
      '  vRedshift = aRedshift;',
      '  vec3 localPos = position;',
      '',
      '  float s = clamp(u_redshift_scale, 0.0, 1.0);',
      '  float z = clamp(aRedshift, 0.0, 1.0);',
      '',
      '  // Phase 2.5: true radial expansion (observer at origin).',
      '  float baseDist = length(localPos);',
      '  vec3 dir = baseDist > 0.0001 ? (localPos / baseDist) : vec3(0.0, 0.0, 1.0);',
      '  float currentDist = baseDist + (z * u_max_depth * s);',
      '  vec3 finalPos = dir * currentDist;',
      '  vWorldPos = finalPos;',
      '',
      '  vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);',
      '  gl_Position = projectionMatrix * mvPosition;',
      '',
      '  // Perspective size attenuation. Keep within a safe pixel range.',
      '  float dist = max(1.0, length(mvPosition.xyz));',
      '  float size = u_size * (300.0 / dist);',
      '  gl_PointSize = clamp(size, 1.0, 250.0);',
      '}',
    ].join('\n'),
    fragmentShader: [
      'precision highp float;',
      'varying float vRedshift;',
      'varying vec3 vWorldPos;',
      'uniform float u_redshift_scale;',
      'uniform float u_opacity;',
      'uniform vec3 u_colorNear;',
      'uniform vec3 u_colorMid;',
      'uniform vec3 u_colorFar;',
      'void main() {',
      '  // Soft particle: draw a glowing disk in the fragment shader.',
      '  vec2 cxy = 2.0 * gl_PointCoord - 1.0;',
      '  float r = dot(cxy, cxy);',
      '  if (r > 1.0) discard;',
      '  // update_patch.md (Cinematic Polish 2.0): fat halo (long tail for overlap).',
      '  float alpha = pow(1.0 - sqrt(r), 2.5);',
      '  float zBurst = clamp(vRedshift * clamp(u_redshift_scale, 0.0, 1.0), 0.0, 1.0);',
      '  // update_patch.md: void exaggeration hack (density mask via low-frequency pseudo-noise).',
      '  float noise = sin(vWorldPos.x * 0.015) * sin(vWorldPos.y * 0.015) * sin(vWorldPos.z * 0.015);',
      '  float densityMask = smoothstep(-0.2, 0.6, noise);',
      '  densityMask = max(0.1, densityMask);',
      '  // Cinematic heatmap palette for depth read (near/mid/far).',
      '  vec3 colorNear = u_colorNear;',
      '  vec3 colorMid  = u_colorMid;',
      '  vec3 colorFar  = u_colorFar;',
      '  vec3 finalColor = mix(colorNear, colorMid, smoothstep(0.0, 0.4, zBurst));',
      '  finalColor = mix(finalColor, colorFar, smoothstep(0.4, 1.0, zBurst));',
      '  finalColor += (colorFar * zBurst * 1.5 * densityMask);',
      '  float depthFade = 1.0 - (zBurst * 0.3);',
      '  gl_FragColor = vec4(finalColor * alpha, clamp(u_opacity, 0.0, 1.0) * densityMask * depthFade);',
      '}',
    ].join('\n'),
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  _macroRedshiftShader = material

  const seed = _hashSeed('oneastro:macro-sky:v1')
  const rng = _mulberry32(seed)
  for (let i = 0; i < count; i += 1) {
    // Historical note: we used to seed a procedural spiral disk here.
    // That is physically wrong for a macro SDSS sky and biases the redshift burst into a cylinder.
    // Use an isotropic sky-sphere distribution as the default baseline.
    const t = i / count
    // Sample dec uniformly by sampling sin(dec) uniformly in [-1,1].
    const ra = rng() * 360
    const dec = coordinateMath.radToDeg(Math.asin((rng() * 2 - 1) || 0))
    const jitter = (rng() - 0.5) * 2.0
    const radius = MACRO_SKY_RADIUS + jitter
    const dir = coordinateMath.raDecToUnitVector(ra + MACRO_RA_OFFSET_DEG, dec)
    positions[i * 3] = dir.x * radius
    positions[i * 3 + 1] = dir.z * radius
    positions[i * 3 + 2] = dir.y * radius

    // Mock redshift values in [0,1]; later replaced by AION output.
    redshift[i] = Math.min(1, Math.max(0, t + (Math.sin(i * 0.015) * 0.08)))
  }

  try {
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('aRedshift', new THREE.BufferAttribute(redshift, 1))
    geometry.setDrawRange(0, count)
    geometry.computeBoundingSphere()
  } catch (_) {
    // ignore
  }

  const mesh = markRaw(new THREE.Points(geometry, material))

  scene.add(mesh)
  macroMesh = mesh

  // Best-effort: inject a small real-data sample into the macro instancing.
  // Never block rendering; always fall back to the procedural spiral if anything fails.
  try {
    queueMicrotask(() => {
      try {
        void _tryInjectSdssMicroSample()
      } catch (_) {
        // ignore
      }
    })
  } catch (_) {
    // ignore
  }

  // Stage 2 Demo 3: modal inpaint shader plane (disabled by default; action-driven).
  try {
    const baseTex = _makeNebulaTexture({
      w: 768,
      h: 512,
      palette: ['#07152e', '#0b2a5a', '#7dd3fc', '#a78bfa'],
      bloomBias: 0.35,
    })
    const predTex = _makeNebulaTexture({
      w: 768,
      h: 512,
      palette: ['#06010f', '#3b0764', '#ec4899', '#fef3c7'],
      bloomBias: 0.85,
    })

    _inpaintUniforms = {
      u_texA: { value: baseTex },
      u_texB: { value: predTex },
      u_center: { value: new THREE.Vector2(0.5, 0.5) },
      u_radius: { value: 0.0 },
      u_edge: { value: 0.06 },
      u_time: { value: 0.0 },
      u_enabled: { value: 0.0 },
      u_layer_opacity: { value: 1.0 },
    }

    const inpaintMat = new THREE.ShaderMaterial({
      uniforms: _inpaintUniforms,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        precision highp float;
        uniform sampler2D u_texA;
        uniform sampler2D u_texB;
        uniform vec2 u_center;
        uniform float u_radius;
        uniform float u_edge;
        uniform float u_time;
        uniform float u_enabled;
        uniform float u_layer_opacity;
        varying vec2 vUv;

        float hash21(vec2 p) {
          p = fract(p * vec2(123.34, 345.45));
          p += dot(p, p + 34.345);
          return fract(p.x * p.y);
        }

        void main() {
          vec4 a = texture2D(u_texA, vUv);
          vec4 b = texture2D(u_texB, vUv);

          float d = distance(vUv, u_center);
          float edge = max(0.002, u_edge);
          float mask = smoothstep(u_radius + edge, u_radius - edge, d);

          // Scanline ring + noisy boundary to avoid a hard cut.
          float ring = smoothstep(0.02, 0.0, abs(d - u_radius));
          float n = hash21(vUv * 1200.0 + u_time * 0.13);
          float spark = ring * (0.55 + 0.45 * n);

          vec4 mixed = mix(a, b, mask);
          mixed.rgb += spark * vec3(0.35, 0.85, 1.25);

          float alpha = clamp(u_enabled, 0.0, 1.0);

          // Edge feather + vignette: kill the rectangular "screenshot" boundary.
          float edgeDist = min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y));
          float edgeFeather = smoothstep(0.0, 0.06, edgeDist);
          float distToCenter = distance(vUv, vec2(0.5, 0.5));
          float vignette = smoothstep(0.55, 0.35, distToCenter);

          float finalAlpha = alpha * clamp(u_layer_opacity, 0.0, 1.0) * edgeFeather * vignette;
          gl_FragColor = vec4(mixed.rgb * finalAlpha, finalAlpha);
        }
      `,
    })

    const inpaintGeo = new THREE.PlaneGeometry(120, 80, 1, 1)
    _inpaintMesh = markRaw(new THREE.Mesh(inpaintGeo, inpaintMat))
    // Put it in front of the macro spiral to reduce spatial intersection artifacts.
    _inpaintMesh.position.set(0, 0, 15)
    _inpaintMesh.visible = false
    _inpaintMesh.renderOrder = 999
    scene.add(_inpaintMesh)
  } catch (_) {
    _inpaintMesh = null
    _inpaintUniforms = null
  }
}

async function _tryInjectSdssMicroSample() {
  if (_sdssInjected) return
  if (!macroMesh || !macroMesh.geometry) return
  if (typeof fetch !== 'function') return

  _sdssInjected = true

  let data
  try {
    const res = await fetch('/data/astronomy/sdss_micro_sample.json', { cache: 'no-cache' })
    if (!res?.ok) return
    data = await res.json()
  } catch (_) {
    return
  }

  if (!Array.isArray(data) || data.length < 1) return

  const parsed = normalizeSdssTriples(data)
  const posAttr0 = macroMesh.geometry.getAttribute('position')
  const capacity = Number(posAttr0?.count) || 100000
  const n = Math.max(1, Math.min(capacity, Number(parsed?.count) || 0))
  if (n < 1 || !Array.isArray(parsed?.flat) || parsed.flat.length < 3) return

  // Visual stability rule (update_patch.md): tiny real-data samples must not collapse the macro starfield.
  // Only switch draw-count to "pure data" mode when the dataset is sufficiently large.
  const PURE_DATA_MIN = 20000
  const radius = MACRO_SKY_RADIUS

  // Normalize redshift into [0,1] while keeping a stable baseline even for tiny samples.
  let zMax = 0
  for (let i = 0; i < n; i += 1) {
    const z = Number(parsed.flat[i * 3 + 2])
    if (Number.isFinite(z)) zMax = Math.max(zMax, z)
  }
  zMax = zMax > 0 ? zMax : 1

  const posAttr = posAttr0
  const redshiftAttr = macroMesh.geometry.getAttribute('aRedshift')
  if (!posAttr?.array || !redshiftAttr?.array) return

  const posArray = posAttr.array
  for (let i = 0; i < n; i += 1) {
    const ra = Number(parsed.flat[i * 3])
    const dec = Number(parsed.flat[i * 3 + 1])
    const z = Number(parsed.flat[i * 3 + 2])
    if (!Number.isFinite(ra) || !Number.isFinite(dec)) continue

    // Map (ra, dec) onto a constant sky-sphere (no flattening).
    const dir = coordinateMath.raDecToUnitVector(ra + MACRO_RA_OFFSET_DEG, dec)
    posArray[i * 3] = dir.x * radius
    posArray[i * 3 + 1] = dir.z * radius
    posArray[i * 3 + 2] = dir.y * radius

    redshiftAttr.array[i] = Number.isFinite(z) ? Math.max(0, Math.min(1, z / zMax)) : 0
  }

  // Keep procedural stars unless we have enough real data to fill the scene.
  try {
    if (n >= PURE_DATA_MIN) macroMesh.geometry.setDrawRange(0, n)
  } catch (_) {
    // ignore
  }

  try {
    posAttr.needsUpdate = true
  } catch (_) {
    // ignore
  }
  try {
    if (redshiftAttr) redshiftAttr.needsUpdate = true
  } catch (_) {
    // ignore
  }

  try {
    macroMesh.geometry.computeBoundingSphere?.()
  } catch (_) {
    // ignore
  }
}

function _makeGottaMarkerTexture({ w = 512, h = 512 } = {}) {
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(128, Math.floor(Number(w) || 512))
  canvas.height = Math.max(128, Math.floor(Number(h) || 512))
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const cx = canvas.width / 2
  const cy = canvas.height / 2
  ctx.fillStyle = '#000000'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Soft radial glow
  const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(cx, cy) * 0.95)
  glow.addColorStop(0.0, 'rgba(255, 255, 255, 0.95)')
  glow.addColorStop(0.18, 'rgba(251, 191, 36, 0.65)')
  glow.addColorStop(0.42, 'rgba(244, 63, 94, 0.25)')
  glow.addColorStop(1.0, 'rgba(0, 0, 0, 0)')
  try {
    ctx.globalCompositeOperation = 'lighter'
  } catch (_) {
    // ignore
  }
  ctx.fillStyle = glow
  ctx.beginPath()
  ctx.arc(cx, cy, Math.min(cx, cy) * 0.58, 0, Math.PI * 2)
  ctx.fill()

  // Crosshair
  try {
    ctx.globalCompositeOperation = 'source-over'
  } catch (_) {
    // ignore
  }
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)'
  ctx.lineWidth = Math.max(2, Math.floor(canvas.width * 0.006))
  ctx.beginPath()
  ctx.arc(cx, cy, Math.min(cx, cy) * 0.28, 0, Math.PI * 2)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(cx - canvas.width * 0.18, cy)
  ctx.lineTo(cx + canvas.width * 0.18, cy)
  ctx.moveTo(cx, cy - canvas.height * 0.18)
  ctx.lineTo(cx, cy + canvas.height * 0.18)
  ctx.stroke()

  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.needsUpdate = true
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  tex.generateMipmaps = true
  return tex
}

function _stopGottaTransient() {
  _gottaActive = false
  try {
    if (_gottaPulseTween) _gottaPulseTween.kill()
  } catch (_) {
    // ignore
  }
  _gottaPulseTween = null

  try {
    if (_gottaDiveTween) _gottaDiveTween.kill()
  } catch (_) {
    // ignore
  }
  _gottaDiveTween = null

  if (_gottaGroup && macroScene) {
    try {
      macroScene.remove(_gottaGroup)
    } catch (_) {
      // ignore
    }
  }
  _gottaGroup = null
  _gottaLastTargetPos = null
}

async function _captureTransientEvent(payload = null) {
  if (!macroScene || !camera) return

  // Scene Authority: keep macro overlays mutually exclusive.
  try {
    if (_inpaintActive) _stopModalInpaint()
  } catch (_) {
    // ignore
  }
  try {
    if (_csstActive) _stopCsstDecomposition({ restoreCamera: false })
  } catch (_) {
    // ignore
  }
  try {
    _setMacroRedshiftScale(0)
  } catch (_) {
    // ignore
  }
  try {
    _stopGottaTransient()
  } catch (_) {
    // ignore
  }

  let eventData = null
  if (payload && typeof payload === 'object' && Number.isFinite(Number(payload?.ra)) && Number.isFinite(Number(payload?.dec))) {
    eventData = {
      eventId: String(payload?.eventId || 'GOTTA-Transient'),
      ra: Number(payload.ra),
      dec: Number(payload.dec),
      type: String(payload?.type || 'Transient'),
      lightcurve: payload?.lightcurve ?? null,
    }
  } else {
    try {
      if (typeof fetch === 'function') {
        const res = await fetch('/data/astronomy/gotta_transient_event.json', { cache: 'no-cache' })
        if (res?.ok) eventData = await res.json()
      }
    } catch (_) {
      // ignore
    }
  }

  // Support both:
  // - Legacy single event object: { eventId, ra, dec, ... }
  // - Network schema: { targetEventId, events: [{ eventId, ra, dec, ... }, ...] }
  const events = Array.isArray(eventData?.events) ? eventData.events : null
  const targetEventId = events ? String(eventData?.targetEventId || payload?.eventId || '') : null
  const targetEvent = events
    ? events.find((e) => String(e?.eventId || '') === targetEventId) || events.find((e) => Number.isFinite(Number(e?.ra)) && Number.isFinite(Number(e?.dec)))
    : eventData

  const ra = Number(targetEvent?.ra)
  const dec = Number(targetEvent?.dec)
  if (!Number.isFinite(ra) || !Number.isFinite(dec)) return

  const radius = MACRO_SKY_RADIUS
  const dir = coordinateMath.raDecToUnitVector(ra + MACRO_RA_OFFSET_DEG, dec)
  const pos = new THREE.Vector3(dir.x * radius, dir.z * radius, dir.y * radius)
  _gottaLastTargetPos = pos.clone()

  if (!_gottaMarkerTexture) {
    try {
      _gottaMarkerTexture = _makeGottaMarkerTexture({ w: 512, h: 512 })
    } catch (_) {
      _gottaMarkerTexture = null
    }
  }

  const g = markRaw(new THREE.Group())

  let targetMarker = null
  const backgroundPositions = []
  if (Array.isArray(events) && events.length) {
    for (const e of events) {
      const era = Number(e?.ra)
      const edec = Number(e?.dec)
      if (!Number.isFinite(era) || !Number.isFinite(edec)) continue
      const edir = coordinateMath.raDecToUnitVector(era + MACRO_RA_OFFSET_DEG, edec)
      const epos = new THREE.Vector3(edir.x * radius, edir.z * radius, edir.y * radius)
      const isTarget = String(e?.eventId || '') === String(targetEvent?.eventId || '')

      const markerMat = new THREE.SpriteMaterial({
        map: _gottaMarkerTexture || null,
        color: isTarget ? 0xffffff : 0xfff7ed,
        transparent: true,
        opacity: isTarget ? 0.92 : 0.14,
        depthTest: false,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
      const marker = markRaw(new THREE.Sprite(markerMat))
      marker.position.copy(epos)
      marker.scale.set(isTarget ? 5.2 : 2.3, isTarget ? 5.2 : 2.3, 1)
      marker.renderOrder = isTarget ? 998 : 996
      g.add(marker)

      if (isTarget) {
        targetMarker = marker
      } else {
        backgroundPositions.push(epos)
      }
    }
  }

  if (!targetMarker) {
    const markerMat = new THREE.SpriteMaterial({
      map: _gottaMarkerTexture || null,
      color: 0xffffff,
      transparent: true,
      opacity: 0.92,
      depthTest: false,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    const marker = markRaw(new THREE.Sprite(markerMat))
    marker.position.copy(pos)
    marker.scale.set(5.2, 5.2, 1)
    marker.renderOrder = 998
    g.add(marker)
    targetMarker = marker
  }

  // A subtle line-of-sight cue from origin.
  try {
    const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), pos.clone()])
    const lineMat = new THREE.LineBasicMaterial({ color: 0xfbbf24, transparent: true, opacity: 0.22 })
    const line = markRaw(new THREE.Line(lineGeo, lineMat))
    line.renderOrder = 997
    g.add(line)
  } catch (_) {
    // ignore
  }

  // Network feel: faint link lines from background events to the target.
  try {
    if (backgroundPositions.length) {
      const pts = []
      for (const p of backgroundPositions) {
        pts.push(p.x, p.y, p.z)
        pts.push(pos.x, pos.y, pos.z)
      }
      const linkGeo = new THREE.BufferGeometry()
      linkGeo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3))
      const linkMat = new THREE.LineBasicMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.08 })
      const links = markRaw(new THREE.LineSegments(linkGeo, linkMat))
      links.renderOrder = 995
      g.add(links)
    }
  } catch (_) {
    // ignore
  }

  macroScene.add(g)
  _gottaGroup = g
  _gottaActive = true

  // Focus camera gently towards the transient marker.
  try {
    if (controls && pos) {
      controls.target.copy(pos)
      controls.update?.()
    }
  } catch (_) {
    // ignore
  }

  // Phase 2.5: spline dive (CatmullRom) to create a high-tension "capture" motion.
  try {
    if (gsap && camera?.position && THREE?.CatmullRomCurve3 && pos) {
      try {
        _gottaDiveTween?.kill?.()
      } catch (_) {
        // ignore
      }

      const prevControlsEnabled = controls ? !!controls.enabled : null
      try {
        if (controls) controls.enabled = false
      } catch (_) {
        // ignore
      }

      const startPos = camera.position.clone()
      // Keep the end position comfortably inside the sky-sphere, even when the marker is far.
      const back = Math.max(12, radius * 0.18)
      const endPos = pos
        .clone()
        .add(pos.clone().normalize().multiplyScalar(-back))
        .add(new THREE.Vector3(7, 4, 14))
      const midPos = startPos.clone().lerp(endPos, 0.5)
      midPos.y += 40
      midPos.x += 30
      const curve = new THREE.CatmullRomCurve3([startPos, midPos, endPos])

      const s = { t: 0 }
      await new Promise((resolve) => {
        _gottaDiveTween = gsap.to(s, {
          t: 1,
          duration: 3.5,
          ease: 'power2.inOut',
          onUpdate: () => {
            try {
              const p = curve.getPoint(Math.max(0, Math.min(1, s.t)))
              camera.position.copy(p)
              if (controls) {
                controls.target.copy(pos)
                controls.update?.()
              }
            } catch (_) {
              // ignore
            }
          },
          onComplete: () => {
            _gottaDiveTween = null
            resolve()
          },
        })
      })

      try {
        if (controls && prevControlsEnabled !== null) controls.enabled = prevControlsEnabled
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }

  // Pulse the marker to convey “capture”.
  try {
    if (gsap && targetMarker?.material) {
      _gottaPulseTween = gsap.to(targetMarker.material, { opacity: 0.25, duration: 0.55, yoyo: true, repeat: -1, ease: 'sine.inOut' })
    }
  } catch (_) {
    // ignore
  }
}

function _makeNebulaTexture({ w = 512, h = 512, palette = [], bloomBias = 0.5 } = {}) {
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(64, Math.floor(w))
  canvas.height = Math.max(64, Math.floor(h))
  const ctx = canvas.getContext('2d')

  // Black background so the inpaint plane (AdditiveBlending) has no "billboard rectangle" edge.
  ctx.fillStyle = '#000000'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Use additive composition in the generator to build organic clouds.
  try {
    ctx.globalCompositeOperation = 'lighter'
  } catch (_) {
    // ignore
  }

  const p = Array.isArray(palette) && palette.length ? palette : ['#050816', '#0b2a5a', '#7dd3fc', '#a78bfa']
  const cx = canvas.width / 2
  const cy = canvas.height / 2

  // Nebula body: many soft blobs.
  for (let i = 0; i < 220; i += 1) {
    const x = cx + (Math.random() - 0.5) * canvas.width * 0.75
    const y = cy + (Math.random() - 0.5) * canvas.height * 0.75
    const r = 20 + Math.random() * 200
    const color = p[Math.floor(Math.random() * p.length)]
    ctx.globalAlpha = (0.02 + Math.random() * 0.08) * (0.5 + bloomBias)
    const blob = ctx.createRadialGradient(x, y, 0, x, y, r)
    blob.addColorStop(0, color)
    blob.addColorStop(1, '#000000')
    ctx.fillStyle = blob
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  // Star dust: higher-frequency specks with center bias.
  ctx.globalAlpha = 0.8
  for (let i = 0; i < 2000; i += 1) {
    const x = cx + (Math.random() - 0.5) * canvas.width * 0.85
    const y = cy + (Math.random() - 0.5) * canvas.height * 0.85
    const dist = Math.hypot(x - cx, y - cy)
    if (dist > canvas.height * 0.45 && Math.random() > 0.15) continue
    const v = 150 + Math.random() * 105
    ctx.fillStyle = `rgb(${v},${v},${v})`
    ctx.fillRect(x, y, 1.2, 1.2)
  }
  ctx.globalAlpha = 1.0

  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.needsUpdate = true
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  tex.generateMipmaps = true
  return tex
}

function _setMacroRedshiftScale(v) {
  _macroRedshiftScale = Math.max(0, Math.min(1, Number(v) || 0))
  const u = macroMesh?.material?.uniforms || _macroRedshiftShader?.uniforms
  if (u?.u_redshift_scale) u.u_redshift_scale.value = _macroRedshiftScale
}

function _setMacroRedshiftMaxDepth(v) {
  const n = Number(v)
  _macroRedshiftMaxDepth = Number.isFinite(n) ? Math.max(1, Math.min(240, n)) : 42
  const u = macroMesh?.material?.uniforms || _macroRedshiftShader?.uniforms
  if (u?.u_max_depth) u.u_max_depth.value = _macroRedshiftMaxDepth
}

function _makeCsstDecomposeTexture({ kind = 'disk', w = 768, h = 512 } = {}) {
  const k = String(kind || 'disk').trim().toLowerCase()
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(256, Math.floor(Number(w) || 768))
  canvas.height = Math.max(256, Math.floor(Number(h) || 512))
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const cx = canvas.width / 2
  const cy = canvas.height / 2

  ctx.fillStyle = '#000000'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  const diskBoost = k === 'disk' ? 1.25 : 0.85
  const bulgeBoost = k === 'bulge' ? 1.35 : 0.85
  const barBoost = k === 'bar' ? 1.30 : 0.90

  // Disk glow (elliptical)
  ctx.save()
  ctx.translate(cx, cy)
  ctx.scale(1.55, 0.82)
  const disk = ctx.createRadialGradient(0, 0, 0, 0, 0, Math.min(cx, cy) * 0.92)
  disk.addColorStop(0.0, `rgba(125, 211, 252, ${0.22 * diskBoost})`)
  disk.addColorStop(0.35, `rgba(56, 189, 248, ${0.14 * diskBoost})`)
  disk.addColorStop(0.75, `rgba(167, 139, 250, ${0.06 * diskBoost})`)
  disk.addColorStop(1.0, 'rgba(0,0,0,0)')
  ctx.fillStyle = disk
  ctx.beginPath()
  ctx.arc(0, 0, Math.min(cx, cy) * 0.92, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()

  // Bulge core
  const bulge = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(cx, cy) * 0.38)
  bulge.addColorStop(0.0, `rgba(254, 243, 199, ${0.32 * bulgeBoost})`)
  bulge.addColorStop(0.35, `rgba(251, 191, 36, ${0.10 * bulgeBoost})`)
  bulge.addColorStop(1.0, 'rgba(0,0,0,0)')
  ctx.fillStyle = bulge
  ctx.beginPath()
  ctx.arc(cx, cy, Math.min(cx, cy) * 0.38, 0, Math.PI * 2)
  ctx.fill()

  // Bar (rotated rectangle glow)
  ctx.save()
  ctx.translate(cx, cy)
  ctx.rotate(-Math.PI * 0.18)
  ctx.globalAlpha = 0.22 * barBoost
  ctx.fillStyle = '#f472b6'
  const bw = canvas.width * 0.52
  const bh = canvas.height * 0.08
  ctx.fillRect(-bw / 2, -bh / 2, bw, bh)
  ctx.globalAlpha = 0.10 * barBoost
  ctx.fillRect(-bw / 2, -bh / 2 - bh * 0.85, bw, bh * 2.7)
  ctx.restore()
  ctx.globalAlpha = 1.0

  // Mild annotation (kept subtle; black stays transparent under additive blending).
  try {
    ctx.font = '600 22px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto'
    ctx.fillStyle = 'rgba(226, 232, 240, 0.70)'
    const label = k === 'bulge' ? 'Bulge' : k === 'bar' ? 'Bar' : 'Disk'
    ctx.fillText(`CSST · ${label}`, 22, 36)
  } catch (_) {
    // ignore
  }

  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.needsUpdate = true
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  tex.generateMipmaps = true
  return tex
}

function _makeFeatheredAdditivePlaneMaterial(tex, { opacity = 0.95, edge = 0.09 } = {}) {
  if (!tex) return null
  return new THREE.ShaderMaterial({
    uniforms: {
      u_tex: { value: tex },
      u_opacity: { value: Math.max(0, Math.min(1, Number(opacity) || 0.95)) },
      u_edge: { value: Math.max(0.001, Math.min(0.25, Number(edge) || 0.09)) },
    },
    vertexShader: [
      'varying vec2 vUv;',
      'void main() {',
      '  vUv = uv;',
      '  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);',
      '}',
    ].join('\n'),
    fragmentShader: [
      'precision highp float;',
      'uniform sampler2D u_tex;',
      'uniform float u_opacity;',
      'uniform float u_edge;',
      'varying vec2 vUv;',
      '',
      'float edgeFeather(vec2 uv, float edge) {',
      '  vec2 a = smoothstep(vec2(0.0), vec2(edge), uv);',
      '  vec2 b = smoothstep(vec2(0.0), vec2(edge), 1.0 - uv);',
      '  return a.x * a.y * b.x * b.y;',
      '}',
      '',
      'float vignette(vec2 uv) {',
      '  float d = distance(uv, vec2(0.5));',
      '  return smoothstep(0.72, 0.22, d);',
      '}',
      '',
      '// Strong circular crop to eliminate any rectangular edge under additive blending.',
      'float circleMask(vec2 uv) {',
      '  float d = distance(uv, vec2(0.5));',
      '  return smoothstep(0.45, 0.25, d);',
      '}',
      '',
      'void main() {',
      '  vec4 t = texture2D(u_tex, vUv);',
      '  float m = edgeFeather(vUv, u_edge) * vignette(vUv) * circleMask(vUv);',
      '  vec3 rgb = t.rgb * m * clamp(u_opacity, 0.0, 1.0);',
      '  float a = clamp(t.a * m * clamp(u_opacity, 0.0, 1.0), 0.0, 1.0);',
      '  gl_FragColor = vec4(rgb, a);',
      '}',
    ].join('\n'),
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
  })
}

function _ensureCsstGroup() {
  if (_csstGroup && _csstPlanes && macroScene) return
  if (!macroScene) return

  const g = markRaw(new THREE.Group())
  g.visible = false
  g.renderOrder = 25

  const textures = [
    _makeCsstDecomposeTexture({ kind: 'disk' }),
    _makeCsstDecomposeTexture({ kind: 'bulge' }),
    _makeCsstDecomposeTexture({ kind: 'bar' }),
  ].filter(Boolean)
  _csstTextures = [...(_csstTextures || []), ...textures]

  const diskMat = _makeFeatheredAdditivePlaneMaterial(textures[0], { opacity: 0.85, edge: 0.10 })
  const bulgeMat = _makeFeatheredAdditivePlaneMaterial(textures[1], { opacity: 0.95, edge: 0.10 })
  const barMat = _makeFeatheredAdditivePlaneMaterial(textures[2], { opacity: 0.90, edge: 0.10 })

  const planeGeo = new THREE.PlaneGeometry(7.2, 4.6, 1, 1)
  const disk = markRaw(new THREE.Mesh(planeGeo, diskMat))
  const bulge = markRaw(new THREE.Mesh(planeGeo, bulgeMat))
  const bar = markRaw(new THREE.Mesh(planeGeo, barMat))

  disk.renderOrder = 25
  bulge.renderOrder = 26
  bar.renderOrder = 27

  g.add(disk)
  g.add(bulge)
  g.add(bar)

  macroScene.add(g)
  _csstGroup = g
  _csstPlanes = { disk, bulge, bar }
}

function _startCsstDecomposition(payload = null) {
  if (!macroScene || !camera) return

  // Scene Authority: CSST overlay must not overlap modal inpaint and should collapse any redshift burst.
  try {
    _stopModalInpaint()
  } catch (_) {
    // ignore
  }
  try {
    _macroRedshiftTween?.kill?.()
  } catch (_) {
    // ignore
  }
  try {
    _setMacroRedshiftScale(0)
  } catch (_) {
    // ignore
  }

  _ensureCsstGroup()
  if (!_csstGroup || !_csstPlanes) return

  const ra = Number(payload?.ra)
  const dec = Number(payload?.dec)
  const radius = Number.isFinite(Number(payload?.radius)) ? Number(payload?.radius) : 12.5
  const useDefault = !(Number.isFinite(ra) && Number.isFinite(dec))
  const baseRa = useDefault ? 150.1 : ra
  const baseDec = useDefault ? 2.22 : dec

  const dir = coordinateMath.raDecToUnitVector(baseRa, baseDec)
  const v = new THREE.Vector3(dir.x, dir.y, dir.z).multiplyScalar(Math.max(4, Math.min(40, radius)))
  _csstTargetPos = v.clone()

  _csstActive = true
  _csstGroup.visible = true
  _csstGroup.position.copy(v)
  _csstGroup.scale.set(0.01, 0.01, 0.01)

  // Freeze initial orientation (avoid continuous billboard which reads like a flat UI card).
  try {
    _csstGroup.quaternion.copy(camera.quaternion)
  } catch (_) {
    // ignore
  }

  // Reset local offsets so repeated triggers remain deterministic.
  try {
    _csstPlanes.disk.position.set(0, 0, 0)
    _csstPlanes.bulge.position.set(0, 0, 0)
    _csstPlanes.bar.position.set(0, 0, 0)

    const tilt = Math.PI / 5
    _csstPlanes.disk.rotation.x = tilt
    _csstPlanes.bulge.rotation.x = tilt
    _csstPlanes.bar.rotation.x = tilt
  } catch (_) {
    // ignore
  }

  // Dim macro stars slightly so the decomposition reads clearly.
  try {
    const u = macroMesh?.material?.uniforms
    if (u?.u_opacity) gsap.to(u.u_opacity, { value: 0.25, duration: 0.7, ease: 'power2.out' })
  } catch (_) {
    // ignore
  }

  try {
    _csstTimeline?.kill?.()
  } catch (_) {
    // ignore
  }

  _csstTimeline = gsap.timeline({ defaults: { ease: 'power2.out' } })
  _csstTimeline.to(_csstGroup.scale, { x: 1, y: 1, z: 1, duration: 0.65 }, 0)
  _csstTimeline.to(_csstPlanes.disk.position, { y: -2.2, z: -2.2, duration: 1.15 }, 0.10)
  _csstTimeline.to(_csstPlanes.bulge.position, { y: 0.0, z: 0.0, duration: 1.15 }, 0.10)
  _csstTimeline.to(_csstPlanes.bar.position, { y: 2.2, z: 2.2, duration: 1.15 }, 0.10)

  // Camera choreography: fly to a stable offset and lock gaze to the target.
  try {
    if (camera?.position && controls) {
      _csstPrevCamPos = camera.position.clone()
      _csstPrevTarget = controls.target?.clone?.() || new THREE.Vector3(0, 0, 0)

      const dirV = v.clone().normalize()
      const up = new THREE.Vector3(0, 1, 0)
      const side = new THREE.Vector3().crossVectors(dirV, up)
      if (side.lengthSq() < 0.0001) side.crossVectors(dirV, new THREE.Vector3(1, 0, 0))
      side.normalize()

      const camPos = v
        .clone()
        .add(dirV.clone().multiplyScalar(7.5))
        .add(up.clone().multiplyScalar(2.4))
        .add(side.clone().multiplyScalar(3.4))

      gsap.to(camera.position, {
        x: camPos.x,
        y: camPos.y,
        z: camPos.z,
        duration: 1.8,
        ease: 'power2.inOut',
        onUpdate: () => {
          try {
            controls.target.copy(v)
            controls.update?.()
          } catch (_) {
            // ignore
          }
        },
      })
    }
  } catch (_) {
    // ignore
  }
}

function _stopCsstDecomposition({ restoreCamera = false } = {}) {
  _csstActive = false

  try {
    _csstTimeline?.kill?.()
  } catch (_) {
    // ignore
  }
  _csstTimeline = null

  if (_csstGroup) {
    try {
      _csstGroup.visible = false
    } catch (_) {
      // ignore
    }
  }

  // Restore macro brightness when leaving CSST overlay.
  try {
    const u = macroMesh?.material?.uniforms
    if (u?.u_opacity) gsap.to(u.u_opacity, { value: _computeMacroOpacityBaseline(), duration: 0.6, ease: 'power2.out' })
  } catch (_) {
    // ignore
  }

  if (restoreCamera && _csstPrevCamPos && camera?.position && controls) {
    try {
      const prevPos = _csstPrevCamPos
      const prevTarget = _csstPrevTarget || new THREE.Vector3(0, 0, 0)
      gsap.to(camera.position, {
        x: prevPos.x,
        y: prevPos.y,
        z: prevPos.z,
        duration: 1.2,
        ease: 'power2.inOut',
        onUpdate: () => {
          try {
            controls.target.copy(prevTarget)
            controls.update?.()
          } catch (_) {
            // ignore
          }
        },
      })
    } catch (_) {
      // ignore
    }
  }
}

async function _executeRedshiftBurst(payload = null) {
  if (!macroMesh) return

  // Phase 2.7: cinematic burst params are layer-store-controlled, with stable defaults.
  const macroL = _getMacroLayerState()
  const burst = macroL?.style?.burst || null
  const burstDollyFov = Number(burst?.dollyFov)
  const burstPushInZ = Number(burst?.pushInZ)
  const burstBloomThr = Number(burst?.bloom?.threshold)
  const burstBloomStr = Number(burst?.bloom?.strength)

  // Cinematic polish (update_patch.md): store values for safe restore.
  let prevFov = null
  let prevZ = null
  let prevBloom = null
  let prevDeepSkyDim = null

  // Scene dominance: redshift burst should never be occluded by modal inpaint.
  try {
    _stopModalInpaint()
  } catch (_) {
    // ignore
  }

  // Scene dominance: redshift burst should not overlap CSST overlays.
  try {
    _stopCsstDecomposition({ restoreCamera: false })
  } catch (_) {
    // ignore
  }

  try {
    _macroRedshiftTween?.kill?.()
  } catch (_) {
    // ignore
  }

  try {
    astroStore.setGenerating(true)
  } catch (_) {
    // ignore
  }

  _setMacroRedshiftMaxDepth(payload?.maxDepth)

  // Ensure every trigger is visually obvious.
  _setMacroRedshiftScale(0)

  try {
    const u = macroMesh?.material?.uniforms
    if (u?.u_opacity) gsap.to(u.u_opacity, { value: _computeMacroOpacityBaseline(), duration: 0.45, ease: 'power2.out' })
  } catch (_) {
    // ignore
  }

  // update_patch.md: dim deep sky background so the burst owns the highlight.
  try {
    if ((_deepSkyMesh?.visible || _deepSkyTextureMesh?.visible) && _deepSkyUniforms?.u_dim) {
      prevDeepSkyDim = Number(_deepSkyUniforms.u_dim.value)
      if (!Number.isFinite(prevDeepSkyDim)) prevDeepSkyDim = 1
      gsap.to(_deepSkyUniforms.u_dim, {
        value: 0.12,
        duration: 2.0,
        ease: 'power2.out',
        onUpdate: () => {
          try {
            _syncDeepSkyTextureOpacity()
          } catch (_) {
            // ignore
          }
        },
      })
    }
  } catch (_) {
    // ignore
  }

  // Cinematic polish: dolly zoom (FOV pull) + gentle push-in.
  try {
    if (camera) {
      prevFov = Number(camera.fov)
      if (camera?.position) prevZ = Number(camera.position.z)

      gsap.to(camera, {
        // Wiring gate default: fov: 95
        fov: Number.isFinite(burstDollyFov) ? burstDollyFov : 95,
        duration: 3.5,
        ease: 'power2.inOut',
        onUpdate: () => {
          try {
            camera.updateProjectionMatrix()
          } catch (_) {
            // ignore
          }
        },
      })

      if (camera?.position && Number.isFinite(prevZ)) {
        gsap.to(camera.position, {
          z: prevZ - (Number.isFinite(burstPushInZ) ? burstPushInZ : 30),
          duration: 3.5,
          ease: 'power2.inOut',
          onUpdate: () => {
            try {
              controls?.update?.()
            } catch (_) {
              // ignore
            }
          },
        })
      }
    }
  } catch (_) {
    // ignore
  }

  // Cinematic polish: tighten bloom so dense clusters ignite into filaments.
  try {
    if (bloomPass) {
      prevBloom = { strength: Number(bloomPass.strength), threshold: Number(bloomPass.threshold) }
      gsap.to(bloomPass, {
        // Wiring gate defaults: threshold: 0.3, strength: 2.8
        threshold: Number.isFinite(burstBloomThr) ? burstBloomThr : 0.3,
        strength: Number.isFinite(burstBloomStr) ? burstBloomStr : 2.8,
        duration: 2.0,
        ease: 'power2.out',
      })
    }
  } catch (_) {
    // ignore
  }

  // Camera choreography: lift up for a more volumetric read, and orbit a bit.
  try {
    void spinMacroCamera({ duration: 6.0, revolutions: 0.5 })
  } catch (_) {
    // ignore
  }
  try {
    if (camera?.position) {
      gsap.to(camera.position, {
        y: Math.max(Number(camera.position.y) || 0, 20),
        duration: 3.5,
        ease: 'power2.out',
        onUpdate: () => {
          try {
            controls?.update?.()
          } catch (_) {
            // ignore
          }
        },
      })
    }
  } catch (_) {
    // ignore
  }

  const state = { v: _macroRedshiftScale }
  await new Promise((resolve) => {
    _macroRedshiftTween = gsap.to(state, {
      v: 1,
      duration: 3.5,
      ease: 'power2.inOut',
      onUpdate: () => _setMacroRedshiftScale(state.v),
      onComplete: resolve,
    })
  })

  try {
    astroStore.setGenerating(false)
  } catch (_) {
    // ignore
  }

  // Restore dolly zoom + bloom to their pre-burst values.
  try {
    if (camera && Number.isFinite(prevFov)) {
      gsap.to(camera, {
        fov: prevFov,
        duration: 1.2,
        ease: 'power2.out',
        onUpdate: () => {
          try {
            camera.updateProjectionMatrix()
          } catch (_) {
            // ignore
          }
        },
      })
    }
  } catch (_) {
    // ignore
  }
  try {
    if (camera?.position && Number.isFinite(prevZ)) gsap.to(camera.position, { z: prevZ, duration: 1.2, ease: 'power2.out' })
  } catch (_) {
    // ignore
  }
  try {
    if (bloomPass && prevBloom && Number.isFinite(prevBloom.threshold) && Number.isFinite(prevBloom.strength)) {
      gsap.to(bloomPass, { threshold: prevBloom.threshold, strength: prevBloom.strength, duration: 1.2, ease: 'power2.out' })
    }
  } catch (_) {
    // ignore
  }

  try {
    if (_deepSkyUniforms?.u_dim && Number.isFinite(prevDeepSkyDim)) {
      gsap.to(_deepSkyUniforms.u_dim, {
        value: prevDeepSkyDim,
        duration: 1.2,
        ease: 'power2.out',
        onUpdate: () => {
          try {
            _syncDeepSkyTextureOpacity()
          } catch (_) {
            // ignore
          }
        },
      })
    }
  } catch (_) {
    // ignore
  }

}

function _startModalInpaint(payload = null) {
  if (!_inpaintMesh || !_inpaintUniforms || !renderer || !camera) return

  // Ensure a clean state (prevents lingering listeners/tweens across rapid switches).
  try {
    _stopModalInpaint()
  } catch (_) {
    // ignore
  }

  // Scene dominance: modal inpaint owns the screen; clear CSST overlays.
  try {
    _stopCsstDecomposition({ restoreCamera: false })
  } catch (_) {
    // ignore
  }

  _inpaintActive = true
  _inpaintMesh.visible = true
  _inpaintUniforms.u_enabled.value = 1.0
  _inpaintUniforms.u_radius.value = 0.0

  // Phase 2.5: anchor the inpaint plane to the GOTTA target / payload position in world space.
  try {
    let anchor = null
    if (payload && typeof payload === 'object') {
      const p = payload?.position || payload?.pos || null
      const px = Number(p?.x ?? payload?.x)
      const py = Number(p?.y ?? payload?.y)
      const pz = Number(p?.z ?? payload?.z)
      if (Number.isFinite(px) && Number.isFinite(py) && Number.isFinite(pz)) {
        anchor = new THREE.Vector3(px, py, pz)
      } else if (Number.isFinite(Number(payload?.ra)) && Number.isFinite(Number(payload?.dec))) {
        const ra = Number(payload.ra)
        const dec = Number(payload.dec)
        const z = Number(payload?.z)
        const dir = coordinateMath.raDecToUnitVector(ra + MACRO_RA_OFFSET_DEG, dec)
        const baseR = MACRO_SKY_RADIUS
        const dist = Number.isFinite(z) ? baseR + z * (Number(_macroRedshiftMaxDepth) || 52) * Math.max(1, _macroRedshiftScale || 1) : baseR
        anchor = new THREE.Vector3(dir.x * dist, dir.z * dist, dir.y * dist)
      }
    }
    if (!anchor && _gottaLastTargetPos) anchor = _gottaLastTargetPos.clone()
    if (anchor) {
      // Offset slightly towards camera to avoid accidental intersection.
      try {
        const toCam = camera.position.clone().sub(anchor)
        const len = toCam.length() || 1
        toCam.multiplyScalar(1 / len)
        anchor.add(toCam.multiplyScalar(1.6))
      } catch (_) {
        // ignore
      }
      _inpaintMesh.position.copy(anchor)
    }
  } catch (_) {
    // ignore
  }

  // Scene dominance: dim the macro spiral so the nebula scan reads clearly.
  try {
    const u = macroMesh?.material?.uniforms
    if (u?.u_opacity) gsap.to(u.u_opacity, { value: 0.05, duration: 1.0, ease: 'power2.out' })
  } catch (_) {
    // ignore
  }

  // Scene dominance 2.0: collapse any existing redshift burst back to 0
  // so expanded particles don't visually "pierce" the inpaint plane.
  try {
    _macroRedshiftTween?.kill?.()
  } catch (_) {
    // ignore
  }
  try {
    _setMacroRedshiftScale(0)
    const u = macroMesh?.material?.uniforms
    if (u?.u_redshift_scale) gsap.to(u.u_redshift_scale, { value: 0.0, duration: 1.5, ease: 'power2.inOut' })
  } catch (_) {
    // ignore
  }

  if (_inpaintClickHandler) return
  _inpaintClickHandler = (ev) => {
    try {
      if (!_inpaintActive || !_inpaintMesh || !_inpaintUniforms || !renderer || !camera) return
      const rect = renderer.domElement.getBoundingClientRect()
      const x = ((ev.clientX - rect.left) / Math.max(1, rect.width)) * 2 - 1
      const y = -(((ev.clientY - rect.top) / Math.max(1, rect.height)) * 2 - 1)

      _inpaintMouse.set(x, y)
      _inpaintRaycaster.setFromCamera(_inpaintMouse, camera)
      const hits = _inpaintRaycaster.intersectObject(_inpaintMesh, false)
      const hit = hits && hits.length ? hits[0] : null
      if (!hit?.uv) return

      _inpaintUniforms.u_center.value.set(hit.uv.x, hit.uv.y)
      _inpaintUniforms.u_radius.value = 0.0

      try {
        _inpaintRadiusTween?.kill?.()
      } catch (_) {
        // ignore
      }

      const s = { r: 0 }
      _inpaintRadiusTween = gsap.to(s, {
        r: 0.55,
        duration: 1.1,
        ease: 'power2.out',
        onUpdate: () => {
          try {
            _inpaintUniforms.u_radius.value = s.r
          } catch (_) {
            // ignore
          }
        },
      })
    } catch (_) {
      // ignore
    }
  }

  try {
    renderer.domElement.addEventListener('pointerdown', _inpaintClickHandler, { passive: true })
  } catch (_) {
    // ignore
  }
}

function _stopModalInpaint() {
  _inpaintActive = false
  try {
    _inpaintRadiusTween?.kill?.()
  } catch (_) {
    // ignore
  }

  if (_inpaintUniforms) {
    try {
      _inpaintUniforms.u_enabled.value = 0.0
      _inpaintUniforms.u_radius.value = 0.0
    } catch (_) {
      // ignore
    }
  }

  if (_inpaintMesh) {
    try {
      _inpaintMesh.visible = false
    } catch (_) {
      // ignore
    }
  }

  if (_inpaintClickHandler && renderer?.domElement) {
    try {
      renderer.domElement.removeEventListener('pointerdown', _inpaintClickHandler)
    } catch (_) {
      // ignore
    }
  }
  _inpaintClickHandler = null

  // Restore macro brightness when leaving inpaint.
  try {
    _restoreCinematicBaseline({ macroOpacity: true, bloom: false, camera: false })
  } catch (_) {
    // ignore
  }
}

function _buildMicroScene(scene) {
  microRoot = markRaw(new THREE.Group())
  scene.add(microRoot)

  const siGeo = new THREE.SphereGeometry(0.11, 10, 10)
  const oGeo = new THREE.SphereGeometry(0.075, 10, 10)
  const siMat = new THREE.MeshPhysicalMaterial({
    color: 0x2563eb,
    transparent: true,
    opacity: 0.88,
    roughness: 0.12,
    metalness: 0.0,
    transmission: 0.82,
    ior: 1.45,
    thickness: 0.6,
  })
  const oMat = new THREE.MeshPhysicalMaterial({
    color: 0xef4444,
    transparent: true,
    opacity: 0.86,
    roughness: 0.16,
    metalness: 0.0,
    transmission: 0.78,
    ior: 1.35,
    thickness: 0.55,
  })
  microMaterial = siMat
  microMaterialO = oMat

  // IMPORTANT: the 3rd argument is the *capacity* of the instance buffers.
  // We later set `.count` to thousands (rebuildMicroLattice), so allocate a safe upper bound.
  microSiMesh = markRaw(new THREE.InstancedMesh(siGeo, siMat, MICRO_MAX_INSTANCES))
  microOMesh = markRaw(new THREE.InstancedMesh(oGeo, oMat, MICRO_MAX_INSTANCES))
  microRoot.add(microSiMesh)
  microRoot.add(microOMesh)

  const bondsGeo = new THREE.BufferGeometry()
  const bondsMat = new THREE.LineBasicMaterial({ color: 0x7dd3fc, transparent: true, opacity: 0.55 })
  microBondLines = markRaw(new THREE.LineSegments(bondsGeo, bondsMat))
  microRoot.add(microBondLines)

  // Default lattice so micro scale is never empty.
  try {
    void rebuildMicroLattice({ type: 'sio2', count: 2400 })
  } catch (_) {
    // ignore
  }
}

function _applyThreeLayerMapping(layers) {
  const mapped = mapLayersToThreeParams(layers)

  if (macroMesh) {
    try {
      macroMesh.visible = !!mapped.macroSpiralVisible
    } catch (_) {
      // ignore
    }
  }

  if (microSiMesh) {
    try {
      microSiMesh.visible = !!mapped.microAtomsVisible
    } catch (_) {
      // ignore
    }
  }

  if (microOMesh) {
    try {
      microOMesh.visible = !!mapped.microAtomsVisible
    } catch (_) {
      // ignore
    }
  }

  if (microBondLines) {
    try {
      microBondLines.visible = !!mapped.microAtomsVisible
      if (microBondLines.material) {
        microBondLines.material.transparent = true
        microBondLines.material.opacity = Math.min(0.9, Math.max(0.08, mapped.microMaterial.opacity * 0.75))
        microBondLines.material.needsUpdate = true
      }
    } catch (_) {
      // ignore
    }
  }

  if (microMaterial) {
    try {
      microMaterial.transparent = true
      microMaterial.opacity = mapped.microMaterial.opacity
      microMaterial.transmission = mapped.microMaterial.transmission
      microMaterial.ior = mapped.microMaterial.ior
      microMaterial.needsUpdate = true
    } catch (_) {
      // ignore
    }
  }

  if (microMaterialO) {
    try {
      microMaterialO.transparent = true
      microMaterialO.opacity = mapped.microMaterial.opacity
      microMaterialO.transmission = mapped.microMaterial.transmission
      microMaterialO.ior = mapped.microMaterial.ior
      microMaterialO.needsUpdate = true
    } catch (_) {
      // ignore
    }
  }

  if (bloomPass) {
    try {
      updateBloomParams(bloomPass, {
        strength: mapped.bloom.enabled ? mapped.bloom.strength : 0,
        threshold: mapped.bloom.threshold,
        radius: mapped.bloom.radius,
      })
    } catch (_) {
      // ignore
    }
  }
}

async function highlightMacroCluster() {
  if (!macroMesh) return
  const mat = macroMesh.material
  if (!mat || !mat.color) return
  try {
    gsap.killTweensOf(mat.color)
  } catch (_) {
    // ignore
  }

  const from = { r: mat.color.r, g: mat.color.g, b: mat.color.b }
  const to = { r: 0.2, g: 1.0, b: 1.0 }

  await new Promise((resolve) => {
    gsap.to(from, {
      r: to.r,
      g: to.g,
      b: to.b,
      duration: 0.45,
      ease: 'power2.out',
      onUpdate: () => {
        try {
          mat.color.setRGB(from.r, from.g, from.b)
        } catch (_) {
          // ignore
        }
      },
      onComplete: () => {
        gsap.to(from, {
          r: 1,
          g: 1,
          b: 1,
          duration: 0.9,
          ease: 'power2.out',
          onUpdate: () => {
            try {
              mat.color.setRGB(from.r, from.g, from.b)
            } catch (_) {
              // ignore
            }
          },
          onComplete: resolve,
        })
      },
    })
  })
}

async function spinMacroCamera({ duration = 3.0, revolutions = 1.0 } = {}) {
  if (!camera) return
  try {
    _macroSpinTween?.kill?.()
  } catch (_) {
    // ignore
  }

  const prevControlsEnabled = controls ? !!controls.enabled : null
  try {
    if (controls) controls.enabled = false
  } catch (_) {
    // ignore
  }

  const r = Math.max(6, Math.hypot(camera.position.x, camera.position.z) || 12)
  const start = Math.atan2(camera.position.z, camera.position.x)
  const state = { t: 0 }

  await new Promise((resolve) => {
    _macroSpinTween = gsap.to(state, {
      t: 1,
      duration: Math.max(0.2, Number(duration) || 3.0),
      ease: 'power1.inOut',
      onUpdate: () => {
        const a = start + state.t * (Math.PI * 2) * (Number(revolutions) || 1.0)
        try {
          camera.position.x = Math.cos(a) * r
          camera.position.z = Math.sin(a) * r
          if (controls) {
            controls.target.set(0, 0, 0)
            controls.update?.()
          }
        } catch (_) {
          // ignore
        }
      },
      onComplete: () => {
        _macroSpinTween = null
        resolve()
      },
    })
  })

  try {
    if (controls && prevControlsEnabled !== null) controls.enabled = prevControlsEnabled
  } catch (_) {
    // ignore
  }
}

async function rebuildMicroLattice(options = {}) {
  if (!microRoot || !microSiMesh || !microOMesh || !microBondLines) return

  const type = String(options?.type || 'sio2').trim().toLowerCase() || 'sio2'
  const countRaw = Number(options?.count)
  const count = Number.isFinite(countRaw) ? Math.max(64, Math.min(12000, Math.floor(countRaw))) : 2400

  // A stable procedural lattice (demo-safe): two species + simple neighbor bonds.
  // Not a physically accurate quartz crystal; optimized for visual clarity + performance.
  const ratioO = type === 'sio2' ? 2 : 1
  const siCap = MICRO_MAX_INSTANCES
  const oCap = MICRO_MAX_INSTANCES
  const siCountWanted = Math.max(1, Math.floor(count / (1 + ratioO)))
  const oCountWanted = Math.max(1, count - siCountWanted)
  const siCount = Math.min(siCap, siCountWanted)
  const oCount = Math.min(oCap, oCountWanted)

  microSiMesh.count = siCount
  microOMesh.count = oCount
  microSiMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  microOMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)

  const rng = _mulberry32(_hashSeed(`${type}:${count}`))
  const tmp = new THREE.Object3D()

  // Build a compact cubic lattice with slight jitter (prevents a "cheap grid" look).
  const grid = Math.ceil(Math.cbrt(Math.max(siCount, oCount)))
  const spacing = 0.32
  const half = (grid - 1) / 2

  const siPos = []
  const oPos = []
  let siIdx = 0
  let oIdx = 0

  for (let x = 0; x < grid && (siIdx < siCount || oIdx < oCount); x += 1) {
    for (let y = 0; y < grid && (siIdx < siCount || oIdx < oCount); y += 1) {
      for (let z = 0; z < grid && (siIdx < siCount || oIdx < oCount); z += 1) {
        // Alternate species placement to create visible structure.
        const parity = (x + y + z) % 2
        const jx = (rng() - 0.5) * 0.06
        const jy = (rng() - 0.5) * 0.06
        const jz = (rng() - 0.5) * 0.06
        const px = (x - half) * spacing + jx
        const py = (y - half) * spacing + jy
        const pz = (z - half) * spacing + jz

        if (parity === 0 && siIdx < siCount) {
          siPos.push(px, py, pz)
          tmp.position.set(px, py, pz)
          tmp.updateMatrix()
          microSiMesh.setMatrixAt(siIdx, tmp.matrix)
          siIdx += 1
        } else if (oIdx < oCount) {
          oPos.push(px, py, pz)
          tmp.position.set(px, py, pz)
          tmp.updateMatrix()
          microOMesh.setMatrixAt(oIdx, tmp.matrix)
          oIdx += 1
        }
      }
    }
  }

  microSiMesh.instanceMatrix.needsUpdate = true
  microOMesh.instanceMatrix.needsUpdate = true

  // Bonds: connect each Si to its nearest O neighbors within a threshold.
  const bondThreshold = 0.55
  const maxBondsPerSi = 4
  const bonds = []

  function dist2(ax, ay, az, bx, by, bz) {
    const dx = ax - bx
    const dy = ay - by
    const dz = az - bz
    return dx * dx + dy * dy + dz * dz
  }

  const thr2 = bondThreshold * bondThreshold
  for (let i = 0; i < siPos.length; i += 3) {
    const ax = siPos[i]
    const ay = siPos[i + 1]
    const az = siPos[i + 2]
    // Find a few nearest O atoms (brute force but bounded by count caps; ok for demo sizes).
    const nearest = []
    for (let j = 0; j < oPos.length; j += 3) {
      const bx = oPos[j]
      const by = oPos[j + 1]
      const bz = oPos[j + 2]
      const d2 = dist2(ax, ay, az, bx, by, bz)
      if (d2 > thr2) continue
      nearest.push({ d2, bx, by, bz })
    }
    nearest.sort((u, v) => u.d2 - v.d2)
    for (let k = 0; k < Math.min(maxBondsPerSi, nearest.length); k += 1) {
      const n = nearest[k]
      bonds.push(ax, ay, az, n.bx, n.by, n.bz)
    }
  }

  // Cap total bonds to avoid huge line buffers.
  const maxFloats = 120000
  const clipped = bonds.length > maxFloats ? bonds.slice(0, maxFloats) : bonds
  const posAttr = new THREE.Float32BufferAttribute(clipped, 3)
  microBondLines.geometry.setAttribute('position', posAttr)
  microBondLines.geometry.computeBoundingSphere()

  // Quick "bond break/reform" vibe: jitter then settle (keeps the old feel, but on real lattice).
  const settle = { t: 0 }
  await new Promise((resolve) => {
    gsap.to(settle, {
      t: 1,
      duration: 0.55,
      ease: 'power2.out',
      onUpdate: () => {
        try {
          microRoot.rotation.y = settle.t * 0.85
          microRoot.rotation.x = settle.t * 0.25
        } catch (_) {
          // ignore
        }
      },
      onComplete: resolve,
    })
  })
}

function initEngine() {
  if (!container.value) return

  renderer = markRaw(new THREE.WebGLRenderer({ antialias: true, alpha: false }))
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setSize(container.value.clientWidth || window.innerWidth, container.value.clientHeight || window.innerHeight)
  container.value.appendChild(renderer.domElement)

  camera = markRaw(
    new THREE.PerspectiveCamera(
      60,
      (container.value.clientWidth || window.innerWidth) / (container.value.clientHeight || window.innerHeight),
      0.1,
      50000
    )
  )
  camera.position.set(0, 8, 24)

  controls = markRaw(new OrbitControls(camera, renderer.domElement))
  controls.enableDamping = true

  macroScene = markRaw(new THREE.Scene())
  microScene = markRaw(new THREE.Scene())
  macroScene.background = new THREE.Color('#050816')
  microScene.background = new THREE.Color('#040608')

  const lightA = new THREE.DirectionalLight(0xffffff, 1.2)
  lightA.position.set(4, 8, 6)
  macroScene.add(lightA)
  microScene.add(lightA.clone())

  const amb = new THREE.AmbientLight(0xffffff, 0.6)
  macroScene.add(amb)
  microScene.add(amb.clone())

  _buildMacroScene(macroScene)
  _buildMicroScene(microScene)

  activeScene = store.currentScale.value === 'micro' ? microScene : macroScene

  const w0 = container.value.clientWidth || window.innerWidth
  const h0 = container.value.clientHeight || window.innerHeight
  try {
    const pp = createBloomPipeline({
      renderer,
      scene: activeScene,
      camera,
      size: { width: w0, height: h0 },
      strength: 1.1,
      threshold: 0.65,
      radius: 0.15,
      classes: {
        EffectComposer,
        RenderPass,
        UnrealBloomPass,
        Vector2: THREE.Vector2,
      },
    })
    composer = markRaw(pp.composer)
    renderPass = markRaw(pp.renderPass)
    bloomPass = markRaw(pp.bloomPass)
  } catch (_) {
    composer = null
    renderPass = null
    bloomPass = null
  }

  // Phase 2.7: snapshot deterministic baselines to avoid long-term drift.
  try {
    if (bloomPass) {
      _bloomBaseline = {
        strength: Number(bloomPass.strength),
        threshold: Number(bloomPass.threshold),
        radius: Number(bloomPass.radius),
      }
    }
  } catch (_) {
    _bloomBaseline = null
  }
  try {
    if (camera) {
      _cameraBaseline = {
        fov: Number(camera.fov),
        z: Number(camera.position?.z),
      }
    }
  } catch (_) {
    _cameraBaseline = null
  }

  // Phase 3+: hover/pick HUD for catalog points.
  try {
    _bindCatalogPointerHandlers()
  } catch (_) {
    // ignore
  }

  // If a deterministic OneAstronomy action was dispatched before ThreeTwin was ready,
  // attempt to run it now (e.g., first click on a preset that also switches scale).
  try {
    _flushPendingAstroAction?.()
  } catch (_) {
    // ignore
  }
  onResize = () => {
    if (!renderer || !camera || !container.value) return
    const w = container.value.clientWidth || window.innerWidth
    const h = container.value.clientHeight || window.innerHeight
    renderer.setSize(w, h)
    try {
      composer?.setSize?.(w, h)
    } catch (_) {
      // ignore
    }
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  }
  window.addEventListener('resize', onResize)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  try {
    controls?.update?.()
  } catch (_) {
    // ignore
  }

  // Astro-GIS Phase 2: animate deep-sky shader (subtle twinkle).
  try {
    if (_deepSkyUniforms?.u_time && _deepSkyMesh?.visible) {
      _deepSkyTime += 1 / 60
      _deepSkyUniforms.u_time.value = _deepSkyTime
    }
  } catch (_) {
    // ignore
  }

  // Keep sky spheres centered on the camera to prevent “leaving the skybox”
  // during large camera translations (dolly/push-in/out / long flights).
  try {
    if (camera) {
      if (_deepSkyMesh?.visible) _deepSkyMesh.position.copy(camera.position)
      if (_deepSkyTextureMesh?.visible) _deepSkyTextureMesh.position.copy(camera.position)
    }
  } catch (_) {
    // ignore
  }

  // Keep texture skybox opacity synced with dim/layer opacity.
  try {
    if (_deepSkyTextureMesh?.visible && _deepSkyTextureMaterial) _syncDeepSkyTextureOpacity()
  } catch (_) {
    // ignore
  }

  // Phase 3+: debounce-fetch catalog points (SIMBAD/VizieR) for the current view.
  try {
    const astro = astroStore.astroGis.value
    const simbadL = astro?.layers?.[ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD] || null
    const vizierL = astro?.layers?.[ASTRO_GIS_LAYER_IDS.CATALOG_VIZIER] || null
    const catL = (vizierL && vizierL.visible) ? vizierL : ((simbadL && simbadL.visible) ? simbadL : null)
    const wanted = !!catL
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
    if (wanted) {
      _catalogWantedVisible = true
      if (!_catalogMesh) _ensureCatalogLayer()
      const view = _computeMacroViewRaDecFov()
      if (view) void _maybeFetchCatalog(catL, view, now)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (renderPass) renderPass.scene = activeScene

    // World-space billboard: keep orientation camera-facing, but do not parent to camera position.
    if (_inpaintActive && _inpaintMesh && camera) {
      try {
        _inpaintMesh.quaternion.copy(camera.quaternion)
      } catch (_) {
        // ignore
      }
    }

    // CSST overlay deliberately does NOT continuously billboard.
    // Keeping a frozen orientation preserves perspective during the side-view camera choreography.

    if (_inpaintUniforms) {
      _inpaintTime += 1 / 60
      _inpaintUniforms.u_time.value = _inpaintTime
    }

    if (composer) composer.render()
    else renderer?.render?.(activeScene, camera)
  } catch (_) {
    // ignore
  }
}

onMounted(() => {
  initEngine()
  _applyThreeLayerMapping(props.layers)
  try {
    _applyAstroGisLayerState(astroStore.astroGis.value)
  } catch (_) {
    // ignore
  }

  // Dev-only manual testing hook (no production dependency).
  try {
    if (import.meta?.env?.DEV) window.__oneearthAstro = astroStore
  } catch (_) {
    // ignore
  }

  animate()
  emit('ready')
})

watch(
  () => astroStore.astroGis.value?.version,
  () => {
    try {
      _applyAstroGisLayerState(astroStore.astroGis.value)
    } catch (_) {
      // ignore
    }
  },
  { immediate: true }
)

watch(
  () => props.layers,
  (v) => {
    try {
      _applyThreeLayerMapping(v)
    } catch (_) {
      // ignore
    }
  },
  { deep: true }
)

watch(
  () => store.currentScale.value,
  (next, prev) => {
    // Scene dominance: inpaint is macro-only; kill it before switching scenes.
    if (String(next || '').trim().toLowerCase() !== 'macro') {
      try {
        if (_inpaintActive) _stopModalInpaint()
      } catch (_) {
        // ignore
      }

      try {
        if (_csstActive) _stopCsstDecomposition({ restoreCamera: false })
      } catch (_) {
        // ignore
      }

      try {
        if (_gottaActive) _stopGottaTransient()
      } catch (_) {
        // ignore
      }
    }
    if (prev === 'macro' && next === 'micro') {
      executeQuantumDive({
        camera,
        gsap,
        settleZ: 16,
        microPose: { x: 0, y: 4, z: 10 },
        onSwitchScene: () => {
          activeScene = microScene
          try {
            if (controls) {
              controls.target.set(0, 0, 0)
              controls.update?.()
            }
          } catch (_) {
            // ignore
          }
        },
      })
      return
    }

    activeScene = next === 'micro' ? microScene : macroScene

    // If a deterministic action arrived before macro scene was active, run it now.
    if (String(next || '').trim().toLowerCase() === 'macro') {
      try {
        _flushPendingAstroAction()
      } catch (_) {
        // ignore
      }
    }
  }
)

watch(
  () => astroStore.currentAgentAction.value?.actionId,
  (id) => {
    if (!id) return
    const action = astroStore.currentAgentAction.value
    try {
      const ran = _tryRunAstroAction(action)
      if (!ran) _pendingAstroAction = action
    } catch (_) {
      _pendingAstroAction = action
    }
  },
  { immediate: true }
)

defineExpose({
  highlightMacroCluster,
  spinMacroCamera,
  rebuildMicroLattice,
  getCamera: () => camera,
})

onBeforeUnmount(() => {
  try {
    window.removeEventListener('resize', onResize)
  } catch (_) {
    // ignore
  }

  try {
    _stopModalInpaint()
  } catch (_) {
    // ignore
  }

  try {
    _stopCsstDecomposition({ restoreCamera: false })
  } catch (_) {
    // ignore
  }

  try {
    _abortCatalogFetch()
  } catch (_) {
    // ignore
  }

  try {
    _unbindCatalogPointerHandlers()
  } catch (_) {
    // ignore
  }
  try {
    _hideCatalogHud()
  } catch (_) {
    // ignore
  }

  disposeThreeEngine({
    renderer,
    controls,
    scenes: [macroScene, microScene],
    disposables: [
      composer,
      bloomPass,
      _inpaintMesh?.material,
      _inpaintMesh?.geometry,
      _catalogMesh?.material,
      _catalogMesh?.geometry,
      _deepSkyTextureMesh?.material,
      _deepSkyTextureMesh?.geometry,
      _deepSkyTextureTex,
      ...(_csstTextures || []),
    ],
    animationId,
    cancelAnimationFrameFn: cancelAnimationFrame,
  })

  _deepSkyMesh = null
  _deepSkyUniforms = null
  _deepSkyTextureMesh = null
  _deepSkyTextureMaterial = null
  _deepSkyTextureTex = null
  _deepSkyTextureWanted = false
  _deepSkyTextureLoadErr = ''

  renderer = null
  camera = null
  controls = null
  macroScene = null
  microScene = null
  activeScene = null
  composer = null
  renderPass = null
  bloomPass = null
  animationId = null
  macroMesh = null
  microRoot = null
  microSiMesh = null
  microOMesh = null
  microBondLines = null
  microMaterial = null
  microMaterialO = null

  _macroRedshiftTween = null
  _macroRedshiftShader = null
  _macroRedshiftScale = 0

  _inpaintMesh = null
  _inpaintUniforms = null
  _inpaintActive = false
  _inpaintClickHandler = null
  _inpaintRadiusTween = null

  _csstGroup = null
  _csstPlanes = null
  _csstActive = false
  _csstTimeline = null
  _csstTargetPos = null
  _csstPrevCamPos = null
  _csstPrevTarget = null
  _csstTextures = []

  _catalogMesh = null
  _catalogUniforms = null
  _catalogWantedVisible = false
  _catalogLastQueryKey = ''
  _catalogLastFetchAt = 0
  _catalogAbort = null

  _catalogActiveLayerId = ''
  _catalogSources = []
  _catalogHoverIndex = -1
  _catalogPinnedIndex = -1
  _catalogPointerMoveHandler = null
  _catalogPointerDownHandler = null

  _bloomBaseline = null
  _cameraBaseline = null
})
</script>

<style scoped>
.three-twin-root {
  position: relative;
}

.three-twin {
  position: relative;
  z-index: 10;
  pointer-events: auto !important;
}

.catalog-hud {
  position: absolute;
  z-index: 20;
  min-width: 180px;
  max-width: 320px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(8, 10, 20, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  pointer-events: none !important;
  transform: translate(0, 0);
}

.catalog-hud-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.catalog-hud-meta {
  margin-top: 2px;
  font-size: 11px;
  opacity: 0.88;
}
</style>
