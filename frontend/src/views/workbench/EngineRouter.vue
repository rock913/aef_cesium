<template>
  <div class="engine-router" aria-label="Engine Router">
    <div class="engine-stack" aria-label="Engine Stack">
      <!-- MVP: always mount Cesium Twin. Three.js modes are Phase 2. -->
      <CesiumViewer
        ref="cesiumViewer"
        :initial-location="initialLocation"
        @viewer-ready="onViewerReady"
      />

      <!-- v7.2: WebGPU sandbox overlay (Event-Driven Overlay). -->
      <canvas
        v-if="showWebGPU"
        ref="gpuCanvas"
        class="webgpu-canvas pointer-events-none"
        aria-label="WebGPU Sandbox Canvas"
      />
    </div>
  </div>
</template>

<script setup>
import * as Cesium from 'cesium'
import { computed, nextTick, ref, watch } from 'vue'
import CesiumViewer from '../../components/CesiumViewer.vue'
import { apiService } from '../../services/api.js'

const props = defineProps({
  scenario: { type: Object, default: null },
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['viewer-ready'])

const cesiumViewer = ref(null)
const cesiumViewerInstance = ref(null)
const overlayHandles = ref(new Map())
const applyToken = ref(0)

const swipeEnabled = ref(false)
const swipePosition = ref(0.5)

// v7.2 WebGPU sandbox overlay state.
const showWebGPU = ref(false)
const gpuCanvas = ref(null)
let _webgpuCleanup = null
let _postRenderUnsub = null
let _webgpuState = null

let _subsurfaceRestore = null

let _nightRestore = null

let _vectorSwipeUnsub = null

function _disableDefaultDoubleClick(viewer) {
  if (!viewer) return
  try {
    const h = viewer?.cesiumWidget?.screenSpaceEventHandler || viewer?.screenSpaceEventHandler
    h?.removeInputAction?.(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
  } catch (_) {
    // ignore
  }
}

function _stopWebGpuOverlay() {
  try {
    if (typeof _webgpuCleanup === 'function') _webgpuCleanup()
  } catch (_) {
    // ignore
  }
  _webgpuCleanup = null

  try {
    if (_postRenderUnsub) {
      _postRenderUnsub()
      _postRenderUnsub = null
    }
  } catch (_) {
    _postRenderUnsub = null
  }

  _webgpuState = null
  showWebGPU.value = false
}

function destroyWebGpuSandbox() {
  _stopWebGpuOverlay()
  return true
}

function _addScenePostRender(viewer, cb) {
  if (!viewer?.scene?.postRender?.addEventListener) return null
  viewer.scene.postRender.addEventListener(cb)
  return () => {
    try {
      viewer.scene.postRender.removeEventListener(cb)
    } catch (_) {
      // ignore
    }
  }
}

async function executeDynamicWgsl(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return { ok: false, reason: 'viewer_not_ready' }

  // WebGPU requires a secure context in all major browsers.
  // If the app is opened via plain http://<public-ip> this will usually fail.
  try {
    if (typeof window !== 'undefined' && window && window.isSecureContext === false) {
      return { ok: false, reason: 'insecure_context', hint: 'WebGPU requires HTTPS (or localhost). Open the site via https://<domain>.' }
    }
  } catch (_) {
    // ignore
  }

  function _gpuErrorToString(err) {
    if (!err) return ''
    try {
      if (typeof err === 'string') return err
      if (typeof err?.message === 'string') return String(err.message)
      return JSON.stringify(err)
    } catch (_) {
      try {
        return String(err)
      } catch (_) {
        return 'unknown_gpu_error'
      }
    }
  }

  function _getUrlParam(key) {
    try {
      if (typeof window === 'undefined') return ''
      const sp = window?.location?.search || ''
      if (!sp) return ''
      const params = new URLSearchParams(sp)
      return String(params.get(key) || '')
    } catch (_) {
      return ''
    }
  }

  function _getWgpuDebugMode() {
    const v = String(_getUrlParam('wgpu_debug') || _getUrlParam('webgpu_debug') || '').trim().toLowerCase()
    if (!v) return ''
    if (v === '1' || v === 'true' || v === 'on') return 'all'
    if (v === 'tint' || v === 'tri' || v === 'all') return v
    return ''
  }

  const urlDebugMode = _getWgpuDebugMode()
  const debugMode = String(options?.debug_mode || options?.wgpu_debug || options?.webgpu_debug || urlDebugMode || '').trim().toLowerCase()
  const debugEnabled = debugMode === 'tint' || debugMode === 'tri' || debugMode === 'all'

  function _extractFirstWgslCodeBlock(s) {
    const t = String(s || '').trim()
    if (!t) return ''
    // If the user pasted markdown, extract the first ```wgsl ... ``` block.
    if (t.includes('```')) {
      const re = /```\s*(wgsl)?\s*\n([\s\S]*?)\n```/gi
      let m = null
      while ((m = re.exec(t))) {
        const lang = String(m[1] || '').trim().toLowerCase()
        const body = String(m[2] || '').trim()
        if (!body) continue
        if (!lang || lang === 'wgsl') return body
      }
    }
    return t
  }

  const wgslRaw = String(options?.wgsl_compute_shader || options?.wgsl || '')
  const wgslInput = _extractFirstWgslCodeBlock(wgslRaw)
  if (!wgslInput) return { ok: false, reason: 'missing_wgsl' }

  // Raw full-modules frequently do: clip = uCamera.proj * uCamera.view * worldPos;
  // Cesium's projection matrix is WebGL clip space (z in [-1, 1]) while WebGPU needs [0, 1].
  // Our wrapped/augmented/fallback templates already include a clip-fix; raw modules may not.
  const rawUsesUCamera = /uCamera\s*\.\s*proj/.test(wgslInput) && /uCamera\s*\.\s*view/.test(wgslInput)
  const rawHasClipFix = /\bclipFix\b/.test(wgslInput)
    || /\.z\s*=\s*\(\s*[^;\n]+\.z\s*\+\s*[^;\n]+\.w\s*\)\s*\*\s*0\.5/.test(wgslInput)
  const rawMayNeedProjClipFix = rawUsesUCamera && !rawHasClipFix

  function _indentLines(s, pad = '  ') {
    return String(s || '')
      .split('\n')
      .map((l) => (l.trim().length ? `${pad}${l}` : l))
      .join('\n')
  }

  function _sanitizeWgslSource(s) {
    const src = String(s || '')
    if (!src) return { code: src, changed: false, replaced: 0 }
    let replaced = 0
    // Some WebGPU/WGSL parsers reject non-ASCII characters (even in comments).
    // Replace with spaces to preserve line breaks and keep diagnostics usable.
    const code = src.replace(/[^\x09\x0A\x0D\x20-\x7E]/g, () => {
      replaced += 1
      return ' '
    })
    return { code, changed: replaced > 0, replaced }
  }

  // Stable template contract for LLM outputs.
  // Accept:
  // - Full WGSL module that defines entryPoints: cs_main/vs_main/fs_main
  // - Compute-body snippet (no @compute / no fn cs_main), which will be wrapped.
  function _looksLikeFullModule(s) {
    const t = String(s || '')
    return /@compute\b/.test(t) || /fn\s+cs_main\s*\(/.test(t) || /@vertex\b/.test(t) || /@fragment\b/.test(t)
  }

  function _hasComputeEntrypoint(s) {
    const t = String(s || '')
    return /@compute\b/.test(t) || /fn\s+cs_main\s*\(/.test(t)
  }

  function _hasVertexEntrypoint(s) {
    const t = String(s || '')
    return /@vertex\b/.test(t) || /fn\s+vs_main\s*\(/.test(t)
  }

  function _hasFragmentEntrypoint(s) {
    const t = String(s || '')
    return /@fragment\b/.test(t) || /fn\s+fs_main\s*\(/.test(t)
  }

  // Some WebGPU implementations appear to be conservative when inferring resource
  // layouts (especially with layout:'auto'), potentially considering resources
  // declared in the module even if unused by a given entrypoint.
  // To avoid "same buffer is both writable and read-only" hazards, we keep a
  // split-module path: compute module has binding(0/2); render module has binding(1/3).
  function _wrapComputeBodyIntoComputeOnlyTemplate(body) {
    const computeBody = _indentLines(String(body || '').trim(), '  ')
    return `
struct Particles {
  data : array<vec4<f32>>,
}

@group(0) @binding(0) var<storage, read_write> particles : Particles;
@group(0) @binding(2) var<uniform> uParams : vec4<f32>; // t, stepScale, particleCount, _

@compute @workgroup_size(256)
fn cs_main(@builtin(global_invocation_id) gid : vec3<u32>) {
${computeBody}
}
`.trim()
  }

  function _buildDefaultRenderOnlyModuleTriangleList() {
    return `
struct Camera {
  view : mat4x4<f32>,
  proj : mat4x4<f32>,
}

struct Particles {
  data : array<vec4<f32>>,
}

@group(0) @binding(1) var<uniform> uCamera : Camera;
@group(0) @binding(3) var<storage, read> particles_ro : Particles;

struct VSOut {
  @builtin(position) Position : vec4<f32>,
  @location(0) color : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  let pid = vid / 6u;
  let corner = vid % 6u;
  let p = particles_ro.data[pid];
  let clipFix = mat4x4<f32>(
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.5, 0.0,
    0.0, 0.0, 0.5, 1.0
  );
  let base = clipFix * uCamera.proj * uCamera.view * vec4<f32>(p.xyz, 1.0);

  var ofs = vec2<f32>(0.0, 0.0);
  if (corner == 0u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 1u) { ofs = vec2<f32>( 1.0, -1.0); }
  else if (corner == 2u) { ofs = vec2<f32>( 1.0,  1.0); }
  else if (corner == 3u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 4u) { ofs = vec2<f32>( 1.0,  1.0); }
  else { ofs = vec2<f32>(-1.0,  1.0); }

  let size = 0.003;
  out.Position = vec4<f32>(base.x + (ofs.x * size * base.w), base.y + (ofs.y * size * base.w), base.z, base.w);
  out.color = vec4<f32>(0.0, 0.95, 1.0, 0.75);
  return out;
}

@fragment
fn fs_main(in : VSOut) -> @location(0) vec4<f32> {
  return in.color;
}
`.trim()
  }

  function _wrapComputeBodyIntoTemplate(body) {
    const computeBody = _indentLines(String(body || '').trim(), '  ')
    return `
struct Camera {
  view : mat4x4<f32>,
  proj : mat4x4<f32>,
}

struct Particles {
  data : array<vec4<f32>>,
}

@group(0) @binding(0) var<storage, read_write> particles : Particles;
@group(0) @binding(3) var<storage, read> particles_ro : Particles;
@group(0) @binding(1) var<uniform> uCamera : Camera;
@group(0) @binding(2) var<uniform> uParams : vec4<f32>; // t, stepScale, particleCount, _

@compute @workgroup_size(256)
fn cs_main(@builtin(global_invocation_id) gid : vec3<u32>) {
${computeBody}
}

struct VSOut {
  @builtin(position) Position : vec4<f32>,
  @location(0) color : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  // Sprite rendering for visibility on high-DPI displays.
  // Each particle expands to 2 triangles (6 vertices).
  let pid = vid / 6u;
  let corner = vid % 6u;
  let p = particles_ro.data[pid];
  // Cesium's projection matrix is WebGL-style clip space (z in [-1, 1]);
  // WebGPU expects z in [0, 1]. Convert so geometry isn't clipped away.
  let clipFix = mat4x4<f32>(
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.5, 0.0,
    0.0, 0.0, 0.5, 1.0
  );
  let base = clipFix * uCamera.proj * uCamera.view * vec4<f32>(p.xyz, 1.0);

  var ofs = vec2<f32>(0.0, 0.0);
  if (corner == 0u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 1u) { ofs = vec2<f32>( 1.0, -1.0); }
  else if (corner == 2u) { ofs = vec2<f32>( 1.0,  1.0); }
  else if (corner == 3u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 4u) { ofs = vec2<f32>( 1.0,  1.0); }
  else { ofs = vec2<f32>(-1.0,  1.0); }

  let size = 0.003;
  out.Position = vec4<f32>(base.x + (ofs.x * size * base.w), base.y + (ofs.y * size * base.w), base.z, base.w);
  out.color = vec4<f32>(0.0, 0.95, 1.0, 0.75);
  return out;
}

@fragment
fn fs_main(in : VSOut) -> @location(0) vec4<f32> {
  return in.color;
}
`.trim()
  }

  // Some wind-field demos output a compute-only WGSL module (cs_main only).
  // If we treat it as a full module, render pipeline creation fails and the overlay
  // appears to do nothing. Best-effort: append default vs_main/fs_main when missing.
  const DEFAULT_RENDER_APPENDIX = `

@group(0) @binding(3) var<storage, read> particles_ro : Particles;

struct VSOut {
  @builtin(position) Position : vec4<f32>,
  @location(0) color : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  let pid = vid / 6u;
  let corner = vid % 6u;
  let p = particles_ro.data[pid];
  let clipFix = mat4x4<f32>(
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.5, 0.0,
    0.0, 0.0, 0.5, 1.0
  );
  let base = clipFix * uCamera.proj * uCamera.view * vec4<f32>(p.xyz, 1.0);

  var ofs = vec2<f32>(0.0, 0.0);
  if (corner == 0u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 1u) { ofs = vec2<f32>( 1.0, -1.0); }
  else if (corner == 2u) { ofs = vec2<f32>( 1.0,  1.0); }
  else if (corner == 3u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 4u) { ofs = vec2<f32>( 1.0,  1.0); }
  else { ofs = vec2<f32>(-1.0,  1.0); }

  let size = 0.003;
  out.Position = vec4<f32>(base.x + (ofs.x * size * base.w), base.y + (ofs.y * size * base.w), base.z, base.w);
  out.color = vec4<f32>(0.0, 0.95, 1.0, 0.75);
  return out;
}

@fragment
fn fs_main(in : VSOut) -> @location(0) vec4<f32> {
  return in.color;
}
`.trim()

  function _augmentComputeOnlyModuleWithDefaultRender(moduleText) {
    return `${String(moduleText || '').trim()}\n\n${DEFAULT_RENDER_APPENDIX}`
  }

  const wrapped = !_looksLikeFullModule(wgslInput)
  const hasCS = _hasComputeEntrypoint(wgslInput)
  const hasVS = _hasVertexEntrypoint(wgslInput)
  const hasFS = _hasFragmentEntrypoint(wgslInput)

  function _findFunctionBlockRange(src, fnName) {
    // Best-effort WGSL block extraction by brace matching.
    // We only need this for cs_main/vs_main/fs_main in our demo modules.
    const s = String(src || '')
    const re = new RegExp(`\\bfn\\s+${fnName}\\s*\\(`)
    const m = re.exec(s)
    if (!m) return null
    const fnIdx = Number(m.index || 0)
    const braceOpen = s.indexOf('{', fnIdx)
    if (braceOpen < 0) return null
    let depth = 0
    for (let i = braceOpen; i < s.length; i += 1) {
      const ch = s[i]
      if (ch === '{') depth += 1
      else if (ch === '}') {
        depth -= 1
        if (depth === 0) {
          return { start: fnIdx, end: i + 1 }
        }
      }
    }
    return null
  }

  function _stripEntrypoint(src, decorator, fnName) {
    // Removes: from the decorator line (e.g. '@compute') up to end of function block.
    const s = String(src || '')
    const r = _findFunctionBlockRange(s, fnName)
    if (!r) return s
    const beforeFn = s.slice(0, r.start)
    const decorIdx = beforeFn.lastIndexOf(String(decorator || ''))
    const start = decorIdx >= 0 ? decorIdx : r.start
    return `${s.slice(0, start).trimEnd()}\n\n${s.slice(r.end).trimStart()}`.trim()
  }

  function _stripBindingVarLines(src, bindings = []) {
    const s = String(src || '')
    const set = new Set((bindings || []).map((b) => String(b)))
    if (!set.size) return s
    const out = s
      .split('\n')
      .filter((line) => {
        const t = String(line || '')
        // Match both '@binding(3)' and '@binding(3) ' styles.
        for (const b of set) {
          if (t.includes(`@binding(${b})`)) return false
        }
        return true
      })
      .join('\n')
    return out.trim()
  }

  function _looksLikeSplitContractRawModule(src) {
    const t = String(src || '')
    const hasRw0 = /@binding\(0\)\s+var<storage,\s*read_write>\s+particles\b/.test(t)
    const hasRo3 = /@binding\(3\)\s+var<storage,\s*read>\s+particles_ro\b/.test(t)
    const hasCam1 = /@binding\(1\)\s+var<uniform>\s+uCamera\b/.test(t)
    const hasParams2 = /@binding\(2\)\s+var<uniform>\s+uParams\b/.test(t)
    return hasRw0 && hasRo3 && hasCam1 && hasParams2
  }

  function _splitRawFullModuleIntoComputeAndRender(src) {
    // Goal: avoid conservative resource reflection pulling render-only bindings into compute.
    // compute module: keep cs_main + binding(0,2), drop vs/fs + binding(1,3)
    // render module: keep vs/fs + binding(1,2,3), drop cs_main + binding(0)
    const raw = String(src || '').trim()
    let compute = raw
    compute = _stripEntrypoint(compute, '@vertex', 'vs_main')
    compute = _stripEntrypoint(compute, '@fragment', 'fs_main')
    compute = _stripBindingVarLines(compute, [1, 3])

    let render = raw
    render = _stripEntrypoint(render, '@compute', 'cs_main')
    render = _stripBindingVarLines(render, [0])

    return { compute, render }
  }

  const topologyOpt = String(options?.topology || '').trim()
  const topologyReq = topologyOpt && ['point-list', 'line-list', 'triangle-list'].includes(topologyOpt)
    ? topologyOpt
    : ''

  const shaderCandidates = []
  if (wrapped) {
    shaderCandidates.push({
      computeCode: _wrapComputeBodyIntoComputeOnlyTemplate(wgslInput),
      renderCode: _buildDefaultRenderOnlyModuleTriangleList(),
      mode: 'wrapped',
      topology: 'triangle-list',
    })
  } else {
    if (hasCS && !hasVS && !hasFS) {
      shaderCandidates.push({ code: _augmentComputeOnlyModuleWithDefaultRender(wgslInput), mode: 'augmented_render', topology: 'triangle-list' })
    }
    // Some WebGPU implementations reflect all declared resources into pipeline layouts
    // even if unused by a given stage. When a full module declares both:
    // - compute RW particles (binding=0)
    // - render RO particles (binding=3)
    // a raw single-module compile can cause compute bind group creation to fail,
    // which triggers a fallback and makes visual updates appear "not applied".
    // Fix: auto-split such raw modules into compute-only + render-only modules.
    if (hasCS && hasVS && hasFS && _looksLikeSplitContractRawModule(wgslInput)) {
      const { compute, render } = _splitRawFullModuleIntoComputeAndRender(wgslInput)
      if (compute && render) {
        shaderCandidates.push({ computeCode: compute, renderCode: render, mode: 'raw_split', topology: topologyReq || 'point-list' })
      }
    }
    shaderCandidates.push({ code: wgslInput, mode: 'raw', topology: topologyReq || 'point-list' })
  }

  // Ensure a clean slate.
  _stopWebGpuOverlay()

  showWebGPU.value = true
  await nextTick()

  // Give layout a chance to settle so getBoundingClientRect() is non-zero.
  // (Some deployments mount the Workbench in a transitioning panel.)
  try {
    await new Promise((resolve) => setTimeout(resolve, 0))
  } catch (_) {
    // ignore
  }

  const canvas = gpuCanvas.value
  if (!canvas) return { ok: false, reason: 'canvas_not_ready' }

  function _measureCanvasPixels() {
    try {
      const dpr = (typeof window !== 'undefined' && Number.isFinite(Number(window.devicePixelRatio)))
        ? Math.max(1, Number(window.devicePixelRatio))
        : 1
      const rect = canvas.getBoundingClientRect?.() || { width: canvas.clientWidth || 0, height: canvas.clientHeight || 0 }
      let cssW = Number(rect.width || 0)
      let cssH = Number(rect.height || 0)
      if (cssW < 2 || cssH < 2) {
        try {
          const p = canvas.parentElement
          const pr = p?.getBoundingClientRect?.() || { width: p?.clientWidth || 0, height: p?.clientHeight || 0 }
          cssW = Math.max(cssW, Number(pr.width || 0))
          cssH = Math.max(cssH, Number(pr.height || 0))
        } catch (_) {
          // ignore
        }
      }
      const w = Math.max(1, Math.floor(cssW * dpr))
      const h = Math.max(1, Math.floor(cssH * dpr))
      return { w, h }
    } catch (_) {
      return { w: 1, h: 1 }
    }
  }

  // Canvas backing store must match CSS size for WebGPU.
  try {
    const { w, h } = _measureCanvasPixels()
    canvas.width = w
    canvas.height = h
  } catch (_) {
    // ignore
  }

  const nav = typeof navigator !== 'undefined' ? navigator : null
  const gpu = nav?.gpu || null
  if (!gpu || typeof gpu.requestAdapter !== 'function') {
    showWebGPU.value = false
    return { ok: false, reason: 'webgpu_unavailable' }
  }

  let adapter = null
  try {
    // Keep this explicit for contract tests and readability.
    adapter = await navigator.gpu.requestAdapter()
  } catch (_) {
    adapter = null
  }
  if (!adapter || typeof adapter.requestDevice !== 'function') {
    showWebGPU.value = false
    return { ok: false, reason: 'no_adapter' }
  }

  let device = null
  try {
    device = await adapter.requestDevice()
  } catch (_) {
    device = null
  }
  if (!device) {
    showWebGPU.value = false
    return { ok: false, reason: 'no_device' }
  }

  // Some implementations report the most actionable errors via uncaptured error events.
  // Capture a short message so `pipeline_failed` can surface it in the Workbench.
  let _lastUncapturedGpuError = ''
  try {
    const onUncaptured = (ev) => {
      try {
        const msg = _gpuErrorToString(ev?.error || ev)
        if (msg) _lastUncapturedGpuError = msg
      } catch (_) {
        // ignore
      }
    }
    if (typeof device.addEventListener === 'function') {
      device.addEventListener('uncapturederror', onUncaptured)
    }
    device.onuncapturederror = onUncaptured
  } catch (_) {
    // ignore
  }

  const ctx = canvas.getContext('webgpu')
  if (!ctx) {
    showWebGPU.value = false
    return { ok: false, reason: 'no_webgpu_context' }
  }

  let format = 'bgra8unorm'
  try {
    if (gpu.getPreferredCanvasFormat) format = gpu.getPreferredCanvasFormat()
  } catch (_) {
    format = 'bgra8unorm'
  }

  try {
    ctx.configure({
      device,
      format,
      alphaMode: 'premultiplied',
    })
  } catch (_) {
    showWebGPU.value = false
    return { ok: false, reason: 'configure_failed' }
  }

  let _lastCanvasW = Number(canvas.width) || 0
  let _lastCanvasH = Number(canvas.height) || 0
  function _syncCanvasSize() {
    try {
      const { w, h } = _measureCanvasPixels()
      if (w === _lastCanvasW && h === _lastCanvasH) return
      _lastCanvasW = w
      _lastCanvasH = h
      canvas.width = w
      canvas.height = h
      ctx.configure({ device, format, alphaMode: 'premultiplied' })
    } catch (_) {
      // ignore
    }
  }

  _syncCanvasSize()

  let _removeResizeListener = null
  try {
    if (typeof window !== 'undefined' && window?.addEventListener) {
      const onResize = () => _syncCanvasSize()
      window.addEventListener('resize', onResize, { passive: true })
      _removeResizeListener = () => {
        try { window.removeEventListener('resize', onResize) } catch (_) { /* ignore */ }
      }
    }
  } catch (_) {
    _removeResizeListener = null
  }

  // v7.2 adaptive degradation: choose a safe particle budget based on device limits.
  const requested = Number(options?.particle_count)
  let particleCount = Number.isFinite(requested) && requested > 0 ? requested : 1000000
  try {
    const maxStorageBuffer = Number(device.limits.maxStorageBufferBindingSize)
    const maxInvocations = Number(device.limits.maxComputeInvocationsPerWorkgroup)
    const requiredBufferSize = particleCount * 16
    if ((Number.isFinite(maxStorageBuffer) && requiredBufferSize > maxStorageBuffer) || (Number.isFinite(maxInvocations) && maxInvocations < 256)) {
      const safe = Number.isFinite(maxStorageBuffer) ? Math.floor((maxStorageBuffer / 16) * 0.8) : 200000
      particleCount = Math.min(Math.max(1000, safe), 200000)
      try {
        console.warn(`[Zero2x WebGPU Sandbox] adaptive degradation -> particleCount=${particleCount}`)
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }

  // Visibility-first: in our templates we render sprites (6 vertices per particle).
  // Keep a conservative cap to avoid fill-rate spikes on laptops.
  try {
    const preset = String(options?.preset || '').trim().toLowerCase()
    // For line-list, each particle is only a segment (2 verts) so we can afford more.
    const reqTopo = String(options?.topology || '').trim().toLowerCase()
    if (preset === 'wind') particleCount = Math.min(particleCount, reqTopo === 'line-list' ? 200000 : 80000)
  } catch (_) {
    // ignore
  }

  const BU = (typeof globalThis !== 'undefined' && globalThis.GPUBufferUsage)
    ? globalThis.GPUBufferUsage
    : { MAP_READ: 0x0001, MAP_WRITE: 0x0002, COPY_SRC: 0x0004, COPY_DST: 0x0008, INDEX: 0x0010, VERTEX: 0x0020, UNIFORM: 0x0040, STORAGE: 0x0080, INDIRECT: 0x0100, QUERY_RESOLVE: 0x0200 }

  // Debug probe: draw a full-screen triangle to validate that the overlay canvas is visible.
  const DEBUG_TRI_WGSL = `
struct VSOut {
  @builtin(position) Position : vec4<f32>,
  @location(0) color : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  // Full-screen triangle (NDC).
  var p = array<vec2<f32>, 3>(
    vec2<f32>(-1.0, -1.0),
    vec2<f32>( 3.0, -1.0),
    vec2<f32>(-1.0,  3.0)
  );
  out.Position = vec4<f32>(p[vid], 0.0, 1.0);
  out.color = vec4<f32>(1.0, 0.95, 0.2, 0.85);
  return out;
}

@fragment
fn fs_main(in : VSOut) -> @location(0) vec4<f32> {
  return in.color;
}
`.trim()

  // Ultra-minimal fallback for maximum portability (no varyings).
  const DEBUG_TRI_WGSL_MIN = `
@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> @builtin(position) vec4<f32> {
  var p = array<vec2<f32>, 3>(
    vec2<f32>(-1.0, -1.0),
    vec2<f32>( 3.0, -1.0),
    vec2<f32>(-1.0,  3.0)
  );
  return vec4<f32>(p[vid], 0.0, 1.0);
}

@fragment
fn fs_main() -> @location(0) vec4<f32> {
  return vec4<f32>(1.0, 0.95, 0.2, 0.9);
}
`.trim()

  // Trail/fade pass: keeps previous frame (loadOp=load) and gently fades existing pixels.
  // IMPORTANT: Avoid darkening the Cesium scene beneath the overlay.
  // We fade by scaling destination (dst *= 1 - srcAlpha), with srcColor=0.
  function _buildFadeWgsl(alpha) {
    const a = Number.isFinite(Number(alpha)) ? Math.min(0.35, Math.max(0.0, Number(alpha))) : 0.08
    return `
struct VSOut {
  @builtin(position) Position : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  var p = array<vec2<f32>, 3>(
    vec2<f32>(-1.0, -1.0),
    vec2<f32>( 3.0, -1.0),
    vec2<f32>(-1.0,  3.0)
  );
  out.Position = vec4<f32>(p[vid], 0.0, 1.0);
  return out;
}

@fragment
fn fs_main() -> @location(0) vec4<f32> {
  // RGB is zero so we don't tint; alpha controls fade strength.
  return vec4<f32>(0.0, 0.0, 0.0, ${a.toFixed(4)});
}
`.trim()
  }

  const FALLBACK_WGSL = `
struct Camera {
  view : mat4x4<f32>,
  proj : mat4x4<f32>,
}

struct Particles {
  data : array<vec4<f32>>,
}

@group(0) @binding(0) var<storage, read_write> particles : Particles;
@group(0) @binding(3) var<storage, read> particles_ro : Particles;
@group(0) @binding(1) var<uniform> uCamera : Camera;
@group(0) @binding(2) var<uniform> uParams : vec4<f32>; // t, stepScale, particleCount, _

fn hash(n: f32) -> f32 { return fract(sin(n) * 43758.5453123); }

// Divergence-free-ish tangent flow on a sphere (curl of a stream function gradient).
fn stream(p: vec3<f32>, t: f32) -> f32 {
  var f = 0.0;
  f += sin(p.x * 4.0 + t) * cos(p.y * 4.0 - t) * 1.0;
  f += sin(p.y * 7.0 - t * 1.2) * cos(p.z * 7.0 + t * 0.8) * 0.5;
  f += sin(p.z * 12.0 + t * 1.5) * cos(p.x * 12.0 - t * 1.1) * 0.25;
  return f;
}

@compute @workgroup_size(256)
fn cs_main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let i = gid.x;
  let n = u32(max(0.0, uParams.z));
  if (i >= n) { return; }
  let t = uParams.x * 0.15;
  let s = max(0.0, uParams.y);
  let dt = max(0.001, (0.016 * clamp(s / 18.0, 0.25, 4.0)));
  var p = particles.data[i];

  // Lifecycle: age decays from 1.0 -> 0.0, respawn on death.
  p.w = p.w - dt * (0.10 + hash(f32(i)) * 0.20);
  if (p.w <= 0.0 || length(p.xyz) < 1.0) {
    p.w = 1.0;
    let seed = f32(i) + t * 100.0;
    let phi = hash(seed) * 6.2831853;
    let costheta = hash(seed * 1.7) * 2.0 - 1.0;
    let theta = acos(costheta);
    p.x = sin(theta) * cos(phi);
    p.y = sin(theta) * sin(phi);
    p.z = cos(theta);
    // Near-earth shell: WGS84 radius (~6,378km) + ~20km troposphere.
    p = vec4<f32>(normalize(p.xyz) * 6398137.0, p.w);
  }

  // Curl-like tangent velocity + zonal jet.
  let pos = normalize(p.xyz);
  let eps = 0.02;
  let dx = stream(pos + vec3<f32>(eps, 0.0, 0.0), t) - stream(pos - vec3<f32>(eps, 0.0, 0.0), t);
  let dy = stream(pos + vec3<f32>(0.0, eps, 0.0), t) - stream(pos - vec3<f32>(0.0, eps, 0.0), t);
  let dz = stream(pos + vec3<f32>(0.0, 0.0, eps), t) - stream(pos - vec3<f32>(0.0, 0.0, eps), t);
  var vel = cross(pos, vec3<f32>(dx, dy, dz) / (2.0 * eps));

  let jet = cross(vec3<f32>(0.0, 0.0, 1.0), pos) * cos(pos.z * 6.0) * 1.5;
  vel = vel + jet;

  p = vec4<f32>(normalize(p.xyz + vel * (dt * 15.0)) * 6398137.0, p.w);
  particles.data[i] = p;
}

struct VSOut {
  @builtin(position) Position : vec4<f32>,
  @location(0) color : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  let pid = vid / 6u;
  let corner = vid % 6u;
  let p = particles_ro.data[pid];
  let clipFix = mat4x4<f32>(
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.5, 0.0,
    0.0, 0.0, 0.5, 1.0
  );
  let base = clipFix * uCamera.proj * uCamera.view * vec4<f32>(p.xyz, 1.0);

  var ofs = vec2<f32>(0.0, 0.0);
  if (corner == 0u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 1u) { ofs = vec2<f32>( 1.0, -1.0); }
  else if (corner == 2u) { ofs = vec2<f32>( 1.0,  1.0); }
  else if (corner == 3u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 4u) { ofs = vec2<f32>( 1.0,  1.0); }
  else { ofs = vec2<f32>(-1.0,  1.0); }

  let size = 0.003;
  out.Position = vec4<f32>(base.x + (ofs.x * size * base.w), base.y + (ofs.y * size * base.w), base.z, base.w);
  // Fade in/out by lifecycle and color-map by latitude.
  let lat = abs(normalize(p.xyz).z);
  let cWarm = vec3<f32>(0.0, 0.95, 1.0);
  let cCool = vec3<f32>(0.6, 0.1, 0.9);
  let alpha = smoothstep(0.0, 0.2, p.w) * smoothstep(1.0, 0.8, p.w);
  out.color = vec4<f32>(mix(cWarm, cCool, lat), alpha * 0.55);
  return out;
}

@fragment
fn fs_main(in : VSOut) -> @location(0) vec4<f32> {
  return in.color;
}
`

  // Always keep a demo-safe fallback that is guaranteed to include compute+render.
  // Prefer split modules to avoid conservative layout reflection in some implementations.
  const FALLBACK_COMPUTE_WGSL = `
struct Particles {
  data : array<vec4<f32>>,
}

@group(0) @binding(0) var<storage, read_write> particles : Particles;
@group(0) @binding(2) var<uniform> uParams : vec4<f32>; // t, stepScale, particleCount, _

fn hash(n: f32) -> f32 { return fract(sin(n) * 43758.5453123); }

fn stream(p: vec3<f32>, t: f32) -> f32 {
  var f = 0.0;
  f += sin(p.x * 4.0 + t) * cos(p.y * 4.0 - t) * 1.0;
  f += sin(p.y * 7.0 - t * 1.2) * cos(p.z * 7.0 + t * 0.8) * 0.5;
  f += sin(p.z * 12.0 + t * 1.5) * cos(p.x * 12.0 - t * 1.1) * 0.25;
  return f;
}

@compute @workgroup_size(256)
fn cs_main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let i = gid.x;
  let n = u32(max(0.0, uParams.z));
  if (i >= n) { return; }
  let t = uParams.x * 0.15;
  let s = max(0.0, uParams.y);
  let dt = max(0.001, (0.016 * clamp(s / 18.0, 0.25, 4.0)));
  var p = particles.data[i];

  p.w = p.w - dt * (0.10 + hash(f32(i)) * 0.20);
  if (p.w <= 0.0 || length(p.xyz) < 1.0) {
    p.w = 1.0;
    let seed = f32(i) + t * 100.0;
    let phi = hash(seed) * 6.2831853;
    let costheta = hash(seed * 1.7) * 2.0 - 1.0;
    let theta = acos(costheta);
    p.x = sin(theta) * cos(phi);
    p.y = sin(theta) * sin(phi);
    p.z = cos(theta);
    // Near-earth shell: WGS84 radius (~6,378km) + ~20km troposphere.
    p = vec4<f32>(normalize(p.xyz) * 6398137.0, p.w);
  }

  let pos = normalize(p.xyz);
  let eps = 0.02;
  let dx = stream(pos + vec3<f32>(eps, 0.0, 0.0), t) - stream(pos - vec3<f32>(eps, 0.0, 0.0), t);
  let dy = stream(pos + vec3<f32>(0.0, eps, 0.0), t) - stream(pos - vec3<f32>(0.0, eps, 0.0), t);
  let dz = stream(pos + vec3<f32>(0.0, 0.0, eps), t) - stream(pos - vec3<f32>(0.0, 0.0, eps), t);
  var vel = cross(pos, vec3<f32>(dx, dy, dz) / (2.0 * eps));

  let jet = cross(vec3<f32>(0.0, 0.0, 1.0), pos) * cos(pos.z * 6.0) * 1.5;
  vel = vel + jet;

  p = vec4<f32>(normalize(p.xyz + vel * (dt * 15.0)) * 6398137.0, p.w);
  particles.data[i] = p;
}
`.trim()

  const FALLBACK_RENDER_WGSL = `
struct Camera {
  view : mat4x4<f32>,
  proj : mat4x4<f32>,
}

struct Particles {
  data : array<vec4<f32>>,
}

@group(0) @binding(1) var<uniform> uCamera : Camera;
@group(0) @binding(3) var<storage, read> particles_ro : Particles;

struct VSOut {
  @builtin(position) Position : vec4<f32>,
  @location(0) color : vec4<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vid : u32) -> VSOut {
  var out : VSOut;
  let pid = vid / 6u;
  let corner = vid % 6u;
  let p = particles_ro.data[pid];
  let clipFix = mat4x4<f32>(
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.5, 0.0,
    0.0, 0.0, 0.5, 1.0
  );
  let base = clipFix * uCamera.proj * uCamera.view * vec4<f32>(p.xyz, 1.0);

  var ofs = vec2<f32>(0.0, 0.0);
  if (corner == 0u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 1u) { ofs = vec2<f32>( 1.0, -1.0); }
  else if (corner == 2u) { ofs = vec2<f32>( 1.0,  1.0); }
  else if (corner == 3u) { ofs = vec2<f32>(-1.0, -1.0); }
  else if (corner == 4u) { ofs = vec2<f32>( 1.0,  1.0); }
  else { ofs = vec2<f32>(-1.0,  1.0); }

  let size = 0.003;
  out.Position = vec4<f32>(base.x + (ofs.x * size * base.w), base.y + (ofs.y * size * base.w), base.z, base.w);
  let lat = abs(normalize(p.xyz).z);
  let cWarm = vec3<f32>(0.0, 0.95, 1.0);
  let cCool = vec3<f32>(0.6, 0.1, 0.9);
  out.color = vec4<f32>(mix(cWarm, cCool, lat), 0.55);
  return out;
}

@fragment
fn fs_main(in : VSOut) -> @location(0) vec4<f32> {
  return in.color;
}
`.trim()

  shaderCandidates.push({ computeCode: FALLBACK_COMPUTE_WGSL, renderCode: FALLBACK_RENDER_WGSL, mode: 'fallback', topology: 'triangle-list' })

  // Uniform buffer for camera matrices (view + proj = 2 * mat4 = 128 bytes).
  let cameraUbo = null
  try {
    cameraUbo = device.createBuffer({
      size: 128,
      usage: (BU.UNIFORM || 0x10) | (BU.COPY_DST || 0x08),
    })
  } catch (_) {
    cameraUbo = null
  }

  // Params buffer for time/step scale (vec4 = 16 bytes).
  let paramsUbo = null
  try {
    paramsUbo = device.createBuffer({
      size: 16,
      usage: (BU.UNIFORM || 0x10) | (BU.COPY_DST || 0x08),
    })
  } catch (_) {
    paramsUbo = null
  }

  // Particle storage buffer: vec4<f32> per particle.
  let particleBuf = null
  try {
    particleBuf = device.createBuffer({
      size: particleCount * 16,
      usage: (BU.STORAGE || 0x80) | (BU.COPY_DST || 0x08),
    })
  } catch (_) {
    particleBuf = null
  }

  const cameraScratch = new Float32Array(32)
  const _clipFix = (Cesium?.Matrix4?.fromArray)
    ? Cesium.Matrix4.fromArray([
      1.0, 0.0, 0.0, 0.0,
      0.0, 1.0, 0.0, 0.0,
      0.0, 0.0, 0.5, 0.0,
      0.0, 0.0, 0.5, 1.0,
    ])
    : null
  const _projScratch = (Cesium?.Matrix4) ? new Cesium.Matrix4() : null
  function _writeCameraUniforms() {
    if (!cameraUbo) return
    try {
      const view = viewer.camera?.viewMatrix
      const proj = viewer.camera?.frustum?.projectionMatrix
      if (!view || !proj || !Cesium.Matrix4) return
      const a = Cesium.Matrix4.toArray(view, new Array(16))

      // For raw full-modules, best-effort pre-multiply projection with clip-fix.
      // This makes raw shaders render correctly without requiring them to manually
      // remap z from [-1, 1] to [0, 1].
      let projToWrite = proj
      if (selectedMode === 'raw' && rawMayNeedProjClipFix && _clipFix && _projScratch && Cesium.Matrix4.multiply) {
        try {
          Cesium.Matrix4.multiply(_clipFix, proj, _projScratch)
          projToWrite = _projScratch
        } catch (_) {
          projToWrite = proj
        }
      }

      const b = Cesium.Matrix4.toArray(projToWrite, new Array(16))
      for (let i = 0; i < 16; i += 1) cameraScratch[i] = Number(a[i])
      for (let i = 0; i < 16; i += 1) cameraScratch[16 + i] = Number(b[i])
      device.queue.writeBuffer(cameraUbo, 0, cameraScratch)
    } catch (_) {
      // ignore
    }
  }

  const paramsScratch = new Float32Array(4)
  let t0 = 0
  function _writeParams() {
    if (!paramsUbo) return
    try {
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
      if (!t0) t0 = now
      const t = (now - t0) / 1000.0

      const stepOpt = Number(options?.step_scale ?? options?.stepScale)
      const preset = String(options?.preset || '').trim().toLowerCase()
      const topoOptRaw = String(options?.topology || '').trim().toLowerCase()
      const topologyOpt = ['point-list', 'line-list', 'triangle-list'].includes(topoOptRaw) ? topoOptRaw : ''
      const stepScale = Number.isFinite(stepOpt)
        ? stepOpt
        : (preset === 'wind'
          ? (topologyOpt === 'line-list' ? 24.0 : 18.0)
          : 1.0)

      paramsScratch[0] = t
      paramsScratch[1] = stepScale
      paramsScratch[2] = Number(particleCount)
      paramsScratch[3] = 0.0
      device.queue.writeBuffer(paramsUbo, 0, paramsScratch)
    } catch (_) {
      // ignore
    }
  }

  function _seedParticles() {
    if (!particleBuf) return
    try {
      const preset = String(options?.preset || '').trim().toLowerCase()
      const seedMode = String(options?.seed || '').trim().toLowerCase()
      const surfaceLike = preset === 'wind' || seedMode === 'surface' || seedMode === 'earth'
      const cinematic = seedMode === 'cinematic'

      const EARTH_RADIUS = 6378137.0
      const SURFACE_OFFSET = 20000.0
      const CINEMATIC_RADIUS = 20000000.0
      const baseRadius = cinematic ? CINEMATIC_RADIUS : (EARTH_RADIUS + SURFACE_OFFSET)

      const arr = new Float32Array(particleCount * 4)
      for (let i = 0; i < particleCount; i += 1) {
        const j = i * 4
        // Global scatter in ECEF meters.
        // Default: near-earth shell (avoids a too-large outer sphere).
        // Opt-in: seed=cinematic uses a much larger radius for “Dyson shell” look.
        const u = (Math.random() * 2.0) - 1.0
        const theta = Math.random() * Math.PI * 2.0
        const s = Math.sqrt(Math.max(0.0, 1.0 - (u * u)))
        const x = s * Math.cos(theta)
        const y = s * Math.sin(theta)
        const z = u
        const thickness = cinematic ? 50000.0 : (surfaceLike ? 25000.0 : 40000.0)
        const jitter = (Math.random() - 0.5) * thickness
        const radius = baseRadius + jitter
        arr[j + 0] = (x * radius)
        arr[j + 1] = (y * radius)
        arr[j + 2] = (z * radius)
        arr[j + 3] = 1.0
      }
      device.queue.writeBuffer(particleBuf, 0, arr)
    } catch (_) {
      // ignore
    }
  }

  _seedParticles()

  // Trails are a key part of the “fluid” illusion (continuous streaks).
  // Default: enabled for Demo13; can be disabled via options.trail=false.
  const presetForTrail = String(options?.preset || '').trim().toLowerCase()
  const trailEnabled = options?.trail === false ? false : true
  const trailAlphaOpt = Number(options?.trail_alpha ?? options?.trailAlpha)
  const topoForTrailRaw = String(options?.topology || '').trim().toLowerCase()
  const topoForTrail = ['point-list', 'line-list', 'triangle-list'].includes(topoForTrailRaw) ? topoForTrailRaw : ''
  const trailAlpha = Number.isFinite(trailAlphaOpt)
    ? trailAlphaOpt
    : (presetForTrail === 'wind'
      ? (topoForTrail === 'line-list' ? 0.05 : 0.08)
      : 0.10)

  let fadePipeline = null
  if (trailEnabled && !debugEnabled) {
    try {
      const fadeMod = device.createShaderModule({ code: _buildFadeWgsl(trailAlpha) })
      fadePipeline = device.createRenderPipeline({
        layout: 'auto',
        vertex: { module: fadeMod, entryPoint: 'vs_main' },
        fragment: {
          module: fadeMod,
          entryPoint: 'fs_main',
          targets: [
            {
              format,
              blend: {
                // dst *= (1 - srcAlpha); srcColor is 0 so we don't tint.
                color: { srcFactor: 'zero', dstFactor: 'one-minus-src-alpha', operation: 'add' },
                alpha: { srcFactor: 'zero', dstFactor: 'one-minus-src-alpha', operation: 'add' },
              },
            },
          ],
        },
        primitive: { topology: 'triangle-list' },
      })
    } catch (_) {
      fadePipeline = null
    }
  }

  let debugTriPipeline = null
  if (debugEnabled) {
    try {
      const mod = device.createShaderModule({ code: DEBUG_TRI_WGSL })
      debugTriPipeline = device.createRenderPipeline({
        layout: 'auto',
        vertex: {
          module: mod,
          entryPoint: 'vs_main',
        },
        fragment: {
          module: mod,
          entryPoint: 'fs_main',
          targets: [{ format }],
        },
        primitive: { topology: 'triangle-list' },
      })
    } catch (_) {
      debugTriPipeline = null
      try {
        const mod = device.createShaderModule({ code: DEBUG_TRI_WGSL_MIN })
        debugTriPipeline = device.createRenderPipeline({
          layout: 'auto',
          vertex: {
            module: mod,
            entryPoint: 'vs_main',
          },
          fragment: {
            module: mod,
            entryPoint: 'fs_main',
            targets: [{ format }],
          },
          primitive: { topology: 'triangle-list' },
        })
      } catch (_) {
        debugTriPipeline = null
      }
    }
  }

  let _debugFrame = 0
  let _debugStartMs = 0
  let _trailPrimed = false
  function _getDebugPhase() {
    if (!debugEnabled) return 'normal'
    const f = Number(_debugFrame) || 0
    const now = (typeof performance !== 'undefined' && performance?.now) ? Number(performance.now()) : Date.now()
    const start = Number(_debugStartMs) || 0
    const elapsed = start > 0 ? Math.max(0, now - start) : 0

    // `tint` / `tri` are meant as quick visibility probes.
    // When explicitly requested via URL/args, keep them persistent so users don't miss them.
    if (debugMode === 'tint') return 'tint'
    if (debugMode === 'tri') return 'tri'
    // debugMode === 'all': cycle for quick diagnosis.
    // Hold each phase for a minimum wall time to avoid “blink and you miss it”.
    if (f < 60 || elapsed < 1500) return 'tint'
    if (f < 120 || elapsed < 3000) return 'tri'
    return 'normal'
  }

  function _renderClearPass(clearValue) {
    try {
      const view = ctx.getCurrentTexture().createView()
      const encoder = device.createCommandEncoder()
      const pass = encoder.beginRenderPass({
        colorAttachments: [
          {
            view,
            clearValue: clearValue || { r: 0, g: 0, b: 0, a: 0 },
            loadOp: 'clear',
            storeOp: 'store',
          },
        ],
      })
      pass.end()
      device.queue.submit([encoder.finish()])
    } catch (_) {
      // ignore
    }
  }

  let computeBindGroup = null
  let renderBindGroup = null
  let computePipeline = null
  let renderPipeline = null
  let pipelineReady = false

  let selectedMode = 'unknown'
  let fallbackUsed = false
  let selectedTopology = 'point-list'

  const diagnostics = {
    bindGroup: null,
    candidates: [],
    uncaptured: null,
  }

  const WEBGPU_SANDBOX_VERSION = 'v7.2-webgpu-diag-20260312.1'

  function _summarizeDiagnostics(diag) {
    const d = diag && typeof diag === 'object' ? diag : {}
    const cands = Array.isArray(d.candidates) ? d.candidates : []
    const lines = []
    for (const c of cands) {
      const mode = String(c?.mode || '').trim() || 'unknown'
      const topo = String(c?.topology || '').trim()
      const comp = String(c?.compilation || '').trim()
      const val = String(c?.validation || '').trim()
      const bg = (c?.compute_bg_ok === false || c?.render_bg_ok === false)
        ? ` bg=compute:${c?.compute_bg_ok ? 'ok' : 'no'}/render:${c?.render_bg_ok ? 'ok' : 'no'}`
        : ''
      const reason = comp
        ? ` comp=${comp}`
        : (val
          ? ` val=${val}`
          : (bg ? ' val=bind_group_mismatch' : ''))
      const t = topo ? ` topo=${topo}` : ''
      if (reason || bg) lines.push(`${mode}${t}${bg}${reason}`)
    }
    if (d.bindGroup?.message) lines.push(String(d.bindGroup.message))
    if (d.uncaptured) lines.push(`uncaptured=${String(d.uncaptured)}`)
    return lines.slice(0, 6).join(' | ')
  }

  async function _popValidationError() {
    try {
      if (!device || typeof device.popErrorScope !== 'function') return null
      return await device.popErrorScope()
    } catch (_) {
      return null
    }
  }

  function _pushValidationScope() {
    try {
      if (!device || typeof device.pushErrorScope !== 'function') return
      device.pushErrorScope('validation')
    } catch (_) {
      // ignore
    }
  }

  async function _tryCreateGpuObject(createFn) {
    // Some implementations report validation errors via error scopes even when
    // object creation is wrapped in try/catch. If we use a single scope for the
    // whole candidate, any failed "try" attempt can poison the candidate even
    // if a later attempt succeeds. Scope each attempt to keep best-effort tries safe.
    _pushValidationScope()
    let obj = null
    let thrown = null
    try {
      obj = createFn()
    } catch (e) {
      thrown = e
    }
    const scopeErr = await _popValidationError()
    const err = scopeErr || thrown
    if (err) return { obj: null, error: err }
    return { obj, error: null }
  }

  async function _createBindGroupAuto(layout, tries) {
    const arr = Array.isArray(tries) ? tries : []
    let lastErr = null
    for (const entries of arr) {
      const res = await _tryCreateGpuObject(() => device.createBindGroup({ layout, entries }))
      if (res?.obj) return { bg: res.obj, error: null }
      if (res?.error) lastErr = res.error
    }
    return { bg: null, error: lastErr }
  }

  try {
    if (cameraUbo && paramsUbo && particleBuf) {
      for (const cand of shaderCandidates) {
        computeBindGroup = null
        renderBindGroup = null
        computePipeline = null
        renderPipeline = null

        let computeModule = null
        let renderModule = null
        let compilationInfoCompute = null
        let compilationInfoRender = null
        let computeSan = { replaced: 0 }
        let renderSan = { replaced: 0 }
        try {
          const computeCodeRaw = String(cand?.computeCode || cand?.code || '')
          const renderCodeRaw = String(cand?.renderCode || cand?.code || '')
          computeSan = _sanitizeWgslSource(computeCodeRaw)
          renderSan = _sanitizeWgslSource(renderCodeRaw)
          const computeCode = String(computeSan?.code || '')
          const renderCode = String(renderSan?.code || '')
          computeModule = computeCode ? device.createShaderModule({ code: computeCode }) : null
          renderModule = renderCode ? device.createShaderModule({ code: renderCode }) : null
        } catch (_) {
          computeModule = null
          renderModule = null
        }

        if (computeModule && typeof computeModule.getCompilationInfo === 'function') {
          try {
            compilationInfoCompute = await computeModule.getCompilationInfo()
          } catch (_) {
            compilationInfoCompute = null
          }
        }

        if (renderModule && typeof renderModule.getCompilationInfo === 'function') {
          try {
            compilationInfoRender = await renderModule.getCompilationInfo()
          } catch (_) {
            compilationInfoRender = null
          }
        }

        let pipelineCreateErr = null
        if (computeModule && renderModule) {
          const computePipeRes = await _tryCreateGpuObject(() => device.createComputePipeline({
            layout: 'auto',
            compute: { module: computeModule, entryPoint: 'cs_main' },
          }))
          computePipeline = computePipeRes?.obj || null
          if (!computePipeline && computePipeRes?.error) pipelineCreateErr = computePipeRes.error

          const renderPipeRes = await _tryCreateGpuObject(() => device.createRenderPipeline({
            layout: 'auto',
            vertex: { module: renderModule, entryPoint: 'vs_main' },
            fragment: {
              module: renderModule,
              entryPoint: 'fs_main',
              targets: [
                {
                  format,
                  blend: {
                    color: { srcFactor: 'src-alpha', dstFactor: 'one-minus-src-alpha', operation: 'add' },
                    alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha', operation: 'add' },
                  },
                },
              ],
            },
            primitive: { topology: String(cand?.topology || 'point-list') },
          }))
          renderPipeline = renderPipeRes?.obj || null
          if (!renderPipeline && renderPipeRes?.error && !pipelineCreateErr) pipelineCreateErr = renderPipeRes.error
        }

        if (computePipeline && renderPipeline) {
          let bindGroupErrMsg = ''
          try {
            const computeLayout0 = computePipeline.getBindGroupLayout(0)
            // Common patterns:
            // - binding(0)=particles storage (rw)
            // - binding(2)=uParams uniform
            // - optionally binding(1)=uCamera uniform
            const computeRes = await _createBindGroupAuto(computeLayout0, [
              [
                { binding: 0, resource: { buffer: particleBuf } },
                { binding: 1, resource: { buffer: cameraUbo } },
                { binding: 2, resource: { buffer: paramsUbo } },
              ],
              [
                { binding: 0, resource: { buffer: particleBuf } },
                { binding: 2, resource: { buffer: paramsUbo } },
              ],
            ])
            computeBindGroup = computeRes?.bg || null
            if (!computeBindGroup && computeRes?.error && !diagnostics.bindGroup) {
              diagnostics.bindGroup = { message: `compute_bind_group_failed: ${_gpuErrorToString(computeRes.error)}` }
            }
            if (!computeBindGroup && computeRes?.error) bindGroupErrMsg = `compute_bind_group_failed: ${_gpuErrorToString(computeRes.error)}`
          } catch (_) {
            computeBindGroup = null
          }

          try {
            const renderLayout0 = renderPipeline.getBindGroupLayout(0)
            // Common patterns:
            // - binding(1)=uCamera uniform
            // - binding(3)=particles read-only-storage
            // - optionally binding(2)=uParams uniform
            const renderRes = await _createBindGroupAuto(renderLayout0, [
              [
                { binding: 1, resource: { buffer: cameraUbo } },
                { binding: 2, resource: { buffer: paramsUbo } },
                { binding: 3, resource: { buffer: particleBuf } },
              ],
              [
                { binding: 1, resource: { buffer: cameraUbo } },
                { binding: 3, resource: { buffer: particleBuf } },
              ],
              [
                { binding: 2, resource: { buffer: paramsUbo } },
                { binding: 3, resource: { buffer: particleBuf } },
              ],
            ])
            renderBindGroup = renderRes?.bg || null
            if (!renderBindGroup && renderRes?.error && !diagnostics.bindGroup) {
              diagnostics.bindGroup = { message: `render_bind_group_failed: ${_gpuErrorToString(renderRes.error)}` }
            }
            if (!renderBindGroup && renderRes?.error) bindGroupErrMsg = `render_bind_group_failed: ${_gpuErrorToString(renderRes.error)}`
          } catch (_) {
            renderBindGroup = null
          }

          if (!computeBindGroup || !renderBindGroup) {
            // Surface bind group failures into the per-candidate validation field.
            // This is especially important when a candidate never becomes "ready".
            if (bindGroupErrMsg && !pipelineCreateErr) pipelineCreateErr = new Error(bindGroupErrMsg)
          }
        }

        const candMsg = _gpuErrorToString(pipelineCreateErr)
        const compMsgsA = Array.isArray(compilationInfoCompute?.messages) ? compilationInfoCompute.messages : []
        const compMsgsB = Array.isArray(compilationInfoRender?.messages) ? compilationInfoRender.messages : []
        const compErrorsA = compMsgsA.filter((m) => String(m?.type || '').toLowerCase() === 'error')
        const compErrorsB = compMsgsB.filter((m) => String(m?.type || '').toLowerCase() === 'error')
        const firstCompError = compErrorsA.length
          ? `${String(compErrorsA[0]?.message || 'WGSL compilation error (compute)')}`
          : (compErrorsB.length ? `${String(compErrorsB[0]?.message || 'WGSL compilation error (render)')}` : '')

        diagnostics.candidates.push({
          mode: String(cand?.mode || ''),
          topology: String(cand?.topology || ''),
          validation: candMsg,
          compilation: firstCompError,
          sanitized_compute: Number(computeSan?.replaced || 0),
          sanitized_render: Number(renderSan?.replaced || 0),
          compute_ok: !!computePipeline,
          render_ok: !!renderPipeline,
          compute_bg_ok: !!computeBindGroup,
          render_bg_ok: !!renderBindGroup,
        })

        if (!computeModule || !renderModule || compErrorsA.length || compErrorsB.length || !computePipeline || !renderPipeline || !computeBindGroup || !renderBindGroup) {
          pipelineReady = false
          computePipeline = null
          renderPipeline = null
          computeBindGroup = null
          renderBindGroup = null
          continue
        }

        pipelineReady = true
        selectedMode = String(cand?.mode || 'unknown')
        fallbackUsed = selectedMode === 'fallback'
        selectedTopology = String(cand?.topology || 'point-list')
        break
      }

      if (!pipelineReady) {
        try {
          const msg = String(_lastUncapturedGpuError || '').trim()
          if (msg) diagnostics.uncaptured = { message: msg }
        } catch (_) {
          // ignore
        }
      }
    }
  } catch (_) {
    pipelineReady = false
    computePipeline = null
    renderPipeline = null
    computeBindGroup = null
    renderBindGroup = null
  }

  if ((!pipelineReady || !computePipeline || !renderPipeline || !computeBindGroup || !renderBindGroup) && !debugEnabled) {
    try {
      // Surface to DevTools for field debugging (some deployments don't display Workbench reports).
      let firstLine = ''
      try {
        const cands = Array.isArray(diagnostics?.candidates) ? diagnostics.candidates : []
        for (const c of cands) {
          const m = String(c?.validation || c?.compilation || '').trim()
          if (m) { firstLine = m.split('\n')[0].slice(0, 260); break }
        }
      } catch (_) {
        firstLine = ''
      }
      if (firstLine) console.error(`[Zero2x WebGPU Sandbox] pipeline_failed summary: ${firstLine}`)
      console.error('[Zero2x WebGPU Sandbox] pipeline_failed', {
        mode: selectedMode,
        topology: selectedTopology,
        particle_count: particleCount,
        canvas_backing_px: { w: Number(canvas?.width) || 0, h: Number(canvas?.height) || 0 },
        bindGroup: diagnostics.bindGroup,
        candidates: diagnostics.candidates,
        uncaptured: diagnostics.uncaptured,
      })
    } catch (_) {
      // ignore
    }
    try {
      cameraUbo?.destroy?.()
    } catch (_) {
      // ignore
    }
    try {
      paramsUbo?.destroy?.()
    } catch (_) {
      // ignore
    }
    try {
      particleBuf?.destroy?.()
    } catch (_) {
      // ignore
    }
    showWebGPU.value = false
    return {
      ok: false,
      reason: 'pipeline_failed',
      wrapped,
      mode: selectedMode,
      error: {
        bindGroup: diagnostics.bindGroup,
        candidates: diagnostics.candidates,
        uncaptured: diagnostics.uncaptured,
      },
    }
  }

  function _computeAndRender() {
    if (!pipelineReady || !computePipeline || !renderPipeline || !computeBindGroup || !renderBindGroup) {
      const phase = _getDebugPhase()
      if (phase === 'tint') {
        _renderClearPass({ r: 1.0, g: 0.0, b: 1.0, a: 0.55 })
        return
      }
      if (phase === 'tri' && debugTriPipeline) {
        // Even if the WGSL pipeline isn't ready, the overlay should show the debug triangle.
        try {
          const view = ctx.getCurrentTexture().createView()
          const encoder = device.createCommandEncoder()
          const rpass = encoder.beginRenderPass({
            colorAttachments: [
              {
                view,
                clearValue: { r: 0, g: 0, b: 0, a: 0 },
                loadOp: 'clear',
                storeOp: 'store',
              },
            ],
          })
          rpass.setPipeline(debugTriPipeline)
          rpass.draw(3, 1, 0, 0)
          rpass.end()
          device.queue.submit([encoder.finish()])
          return
        } catch (_) {
          // fall through
        }
      }
      _renderClearPass({ r: 0, g: 0, b: 0, a: 0 })
      return
    }
    try {
      const phase = _getDebugPhase()
      const encoder = device.createCommandEncoder()

      // For debug probes, skip compute so we isolate overlay visibility.
      if (phase === 'normal') {
        const cpass = encoder.beginComputePass()
        cpass.setPipeline(computePipeline)
        cpass.setBindGroup(0, computeBindGroup)
        const wg = 256
        const workgroups = Math.ceil(particleCount / wg)
        cpass.dispatchWorkgroups(workgroups)
        cpass.end()
      }

      // Render pass (draw points into transparent overlay).
      const view = ctx.getCurrentTexture().createView()
      const shouldTrail = phase === 'normal' && trailEnabled && !!fadePipeline
      const loadOp = (shouldTrail && _trailPrimed) ? 'load' : 'clear'
      const clearValue = phase === 'tint' ? { r: 1.0, g: 0.0, b: 1.0, a: 0.55 } : { r: 0, g: 0, b: 0, a: 0 }
      const rpass = encoder.beginRenderPass({
        colorAttachments: [
          {
            view,
            clearValue,
            loadOp,
            storeOp: 'store',
          },
        ],
      })

      // Fade pass first (keeps previous pixels but decays them).
      if (shouldTrail && _trailPrimed && fadePipeline) {
        rpass.setPipeline(fadePipeline)
        rpass.draw(3, 1, 0, 0)
      }

      if (phase === 'tri' && debugTriPipeline) {
        rpass.setPipeline(debugTriPipeline)
        rpass.draw(3, 1, 0, 0)
      } else if (phase === 'tint') {
        // Tint probe: clear only (no draws) so the magenta overlay is unmistakable.
      } else {
        rpass.setPipeline(renderPipeline)
        rpass.setBindGroup(0, renderBindGroup)
        const vertexCount = selectedTopology === 'triangle-list'
          ? (particleCount * 6)
          : (selectedTopology === 'line-list' ? (particleCount * 2) : particleCount)
        rpass.draw(vertexCount, 1, 0, 0)
      }
      rpass.end()

      if (phase === 'normal' && trailEnabled) _trailPrimed = true

      device.queue.submit([encoder.finish()])
    } catch (_) {
      _renderClearPass()
    }
  }

  // Event-driven overlay: sync on Cesium postRender.
  const unsub = _addScenePostRender(viewer, () => {
    if (debugEnabled && !_debugStartMs) {
      try {
        _debugStartMs = (typeof performance !== 'undefined' && performance?.now) ? Number(performance.now()) : Date.now()
      } catch (_) {
        _debugStartMs = Date.now()
      }
    }
    if (debugEnabled) _debugFrame += 1
    _syncCanvasSize()
    _writeCameraUniforms()
    _writeParams()
    _computeAndRender()
  })
  _postRenderUnsub = unsub

  const vertexCount = (pipelineReady && selectedTopology === 'triangle-list')
    ? (particleCount * 6)
    : (pipelineReady
      ? (selectedTopology === 'line-list' ? (particleCount * 2) : particleCount)
      : 0)
  const canvas_backing_px = {
    w: Number(canvas?.width) || 0,
    h: Number(canvas?.height) || 0,
  }
  _webgpuState = { device, ctx, format, particleCount, vertexCount, cameraUbo, paramsUbo, particleBuf, pipelineReady, fallbackUsed, mode: selectedMode, topology: selectedTopology, debug_mode: debugEnabled ? debugMode : '' }

  _webgpuCleanup = () => {
    try {
      if (_postRenderUnsub) _postRenderUnsub()
    } catch (_) {
      // ignore
    }
    _postRenderUnsub = null
    try {
      if (typeof _removeResizeListener === 'function') _removeResizeListener()
    } catch (_) {
      // ignore
    }
    _removeResizeListener = null
    try {
      cameraUbo?.destroy?.()
    } catch (_) {
      // ignore
    }
    try {
      paramsUbo?.destroy?.()
    } catch (_) {
      // ignore
    }
    try {
      particleBuf?.destroy?.()
    } catch (_) {
      // ignore
    }
  }

  if (!pipelineReady || !computePipeline || !renderPipeline || !computeBindGroup || !renderBindGroup) {
    // Keep the overlay alive in debug modes (tri/tint), but report failure with diagnostics.
    try {
      let firstLine = ''
      try {
        const cands = Array.isArray(diagnostics?.candidates) ? diagnostics.candidates : []
        for (const c of cands) {
          const m = String(c?.validation || c?.compilation || '').trim()
          if (m) { firstLine = m.split('\n')[0].slice(0, 260); break }
        }
      } catch (_) {
        firstLine = ''
      }
      if (firstLine) console.error(`[Zero2x WebGPU Sandbox] pipeline_failed summary: ${firstLine}`)
      console.error('[Zero2x WebGPU Sandbox] pipeline_failed (debug mode)', {
        mode: selectedMode,
        topology: selectedTopology,
        particle_count: particleCount,
        canvas_backing_px: { w: Number(canvas?.width) || 0, h: Number(canvas?.height) || 0 },
        bindGroup: diagnostics.bindGroup,
        candidates: diagnostics.candidates,
        uncaptured: diagnostics.uncaptured,
      })
    } catch (_) {
      // ignore
    }
    return {
      ok: false,
      reason: 'pipeline_failed',
      particle_count: particleCount,
      vertex_count: vertexCount,
      canvas_backing_px,
      fallback_used: fallbackUsed,
      pipeline_ready: pipelineReady,
      wrapped,
      mode: selectedMode,
      topology: selectedTopology,
      debug_mode: debugEnabled ? debugMode : '',
      error: {
        bindGroup: diagnostics.bindGroup,
        candidates: diagnostics.candidates,
        uncaptured: diagnostics.uncaptured,
      },
    }
  }

  const diagSummary = _summarizeDiagnostics(diagnostics)
  const wantDiag = debugEnabled || fallbackUsed

  if (wantDiag) {
    try {
      const title = fallbackUsed
        ? '[Zero2x WebGPU Sandbox] fallback_used'
        : '[Zero2x WebGPU Sandbox] debug'
      // Console logging is critical for diagnosing vendor-specific layout:'auto' issues.
      // Keep it collapsed by default to avoid noisy logs.
      console.groupCollapsed(title)
      console.info('summary:', diagSummary || '(empty)')
      console.info('selected:', { mode: selectedMode, topology: selectedTopology, particle_count: particleCount, vertex_count: vertexCount })
      console.info('bindGroup:', diagnostics.bindGroup)
      console.info('candidates:', diagnostics.candidates)
      if (diagnostics.uncaptured) console.info('uncaptured:', diagnostics.uncaptured)
      console.info('version:', WEBGPU_SANDBOX_VERSION)
      console.groupEnd()
    } catch (_) {
      // ignore
    }
  }

  return {
    ok: true,
    particle_count: particleCount,
    vertex_count: vertexCount,
    canvas_backing_px,
    fallback_used: fallbackUsed,
    pipeline_ready: pipelineReady,
    wrapped,
    mode: selectedMode,
    topology: selectedTopology,
    debug_mode: debugEnabled ? debugMode : '',
    webgpu_sandbox_version: WEBGPU_SANDBOX_VERSION,
    diagnostics: wantDiag
      ? { bindGroup: diagnostics.bindGroup, candidates: diagnostics.candidates, summary: diagSummary }
      : undefined,
  }
}

function enableSubsurfaceMode(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  // Capture previous state once so we can restore later.
  if (!_subsurfaceRestore) {
    try {
      const globe = viewer.scene?.globe
      const ctrl = viewer.scene?.screenSpaceCameraController
      const translucency = globe?.translucency

      let undergroundColor = null
      try {
        if (globe && globe.undergroundColor && Cesium?.Color?.clone) undergroundColor = Cesium.Color.clone(globe.undergroundColor)
        else if (globe && globe.undergroundColor) undergroundColor = globe.undergroundColor
      } catch (_) {
        undergroundColor = null
      }

      const prev = {
        collision: ctrl ? !!ctrl.enableCollisionDetection : null,
        translucencyEnabled: translucency ? !!translucency.enabled : null,
        frontFaceAlpha: translucency ? translucency.frontFaceAlpha : null,
        backFaceAlpha: translucency ? translucency.backFaceAlpha : null,
        frontFaceAlphaByDistance: translucency ? translucency.frontFaceAlphaByDistance : null,
        backFaceAlphaByDistance: translucency ? translucency.backFaceAlphaByDistance : null,
        undergroundColor,
      }
      _subsurfaceRestore = () => {
        try {
          if (ctrl && typeof prev.collision === 'boolean') ctrl.enableCollisionDetection = prev.collision
        } catch (_) {
          // ignore
        }
        try {
          if (translucency && typeof prev.translucencyEnabled === 'boolean') translucency.enabled = prev.translucencyEnabled
        } catch (_) {
          // ignore
        }
        try {
          if (translucency && prev.frontFaceAlphaByDistance) translucency.frontFaceAlphaByDistance = prev.frontFaceAlphaByDistance
        } catch (_) {
          // ignore
        }
        try {
          if (translucency && prev.backFaceAlphaByDistance) translucency.backFaceAlphaByDistance = prev.backFaceAlphaByDistance
        } catch (_) {
          // ignore
        }
        try {
          if (translucency && typeof prev.frontFaceAlpha === 'number') translucency.frontFaceAlpha = prev.frontFaceAlpha
        } catch (_) {
          // ignore
        }
        try {
          if (translucency && typeof prev.backFaceAlpha === 'number') translucency.backFaceAlpha = prev.backFaceAlpha
        } catch (_) {
          // ignore
        }

        try {
          if (globe && prev.undergroundColor) globe.undergroundColor = prev.undergroundColor
        } catch (_) {
          // ignore
        }
      }
    } catch (_) {
      _subsurfaceRestore = null
    }
  }

  const tr = Number(options?.transparency)
  const transparency = Number.isFinite(tr) ? Math.max(0, Math.min(1, tr)) : 0.2
  const depthRaw = Number(options?.target_depth_meters)
  const depth = Number.isFinite(depthRaw) ? Math.abs(depthRaw) : null

  try {
    const globe = viewer.scene?.globe
    if (globe?.translucency) {
      globe.translucency.enabled = true
      // 0303 patch: avoid alpha-by-distance. Keep the globe instantly "cyber crystal"
      // even from a far camera, so the audience sees the effect immediately.
      try {
        globe.translucency.frontFaceAlphaByDistance = null
      } catch (_) {
        // ignore
      }
      try {
        globe.translucency.backFaceAlphaByDistance = null
      } catch (_) {
        // ignore
      }
      try {
        globe.translucency.frontFaceAlpha = transparency
      } catch (_) {
        // ignore
      }
      try {
        globe.translucency.backFaceAlpha = transparency
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }

  // 0303 patch: avoid a pure-black underground mask.
  try {
    const globe = viewer.scene?.globe
    if (globe && globe.undergroundColor && Cesium?.Color?.fromCssColorString) {
      globe.undergroundColor = Cesium.Color.fromCssColorString('#00141A').withAlpha(1.0)
    }
  } catch (_) {
    // ignore
  }

  try {
    if (viewer.scene?.screenSpaceCameraController) {
      viewer.scene.screenSpaceCameraController.enableCollisionDetection = false
    }
  } catch (_) {
    // ignore
  }

  // Best-effort: if a target depth is given, dive below the surface at current lon/lat.
  if (depth) {
    try {
      const carto = Cesium.Cartographic.fromCartesian(viewer.camera.position)
      const dest = Cesium.Cartesian3.fromRadians(carto.longitude, carto.latitude, -depth)
      viewer.camera.flyTo({ destination: dest, duration: 1.2 })
    } catch (_) {
      // ignore
    }
  }

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
  return true
}

function disableSubsurfaceMode() {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  _removeOverlayEntry(_RUNTIME_KEYS.subsurfaceModel)

  try {
    if (typeof _subsurfaceRestore === 'function') _subsurfaceRestore()
  } catch (_) {
    // ignore
  }
  _subsurfaceRestore = null

  // Best-effort safety defaults even if snapshot failed.
  try {
    const globe = viewer.scene?.globe
    if (globe?.translucency) {
      globe.translucency.enabled = false
    }
  } catch (_) {
    // ignore
  }
  try {
    if (viewer.scene?.screenSpaceCameraController) {
      viewer.scene.screenSpaceCameraController.enableCollisionDetection = true
    }
  } catch (_) {
    // ignore
  }

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }

  return true
}

async function addSubsurfaceModel(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  _removeOverlayEntry(_RUNTIME_KEYS.subsurfaceModel)

  const lat = Number(options?.lat)
  const lon = Number(options?.lon)
  const depth = Number(options?.depth)
  const lat0 = Number.isFinite(lat) ? lat : -22.3
  const lon0 = Number.isFinite(lon) ? lon : 118.7
  const depth0 = Number.isFinite(depth) ? depth : -3800.0

  try {
    const points = viewer.scene?.primitives?.add?.(new Cesium.PointPrimitiveCollection())
    if (!points) return false

    const origin = Cesium.Cartesian3.fromDegrees(lon0, lat0, depth0)
    const enu = Cesium.Transforms.eastNorthUpToFixedFrame(origin)

    const baseColor = Cesium.Color.fromCssColorString('#FF4D6D')
    const countRaw = Number(options?.count)
    const count = Number.isFinite(countRaw) ? Math.max(500, Math.min(20000, Math.floor(countRaw))) : 6500

    const spanXYRaw = Number(options?.span_xy_m)
    const spanZRaw = Number(options?.span_z_m)
    const pixelSizeRaw = Number(options?.pixel_size)

    const spanXY = Number.isFinite(spanXYRaw) ? Math.max(200.0, Math.min(20000.0, spanXYRaw)) : 3200.0
    const spanZ = Number.isFinite(spanZRaw) ? Math.max(200.0, Math.min(20000.0, spanZRaw)) : 1500.0
    const basePixelSize = Number.isFinite(pixelSizeRaw) ? Math.max(1.0, Math.min(18.0, pixelSizeRaw)) : 4.0

    for (let i = 0; i < count; i += 1) {
      const rx = (Math.random() - 0.5) * spanXY
      const ry = (Math.random() - 0.5) * spanXY
      const rz = -Math.random() * spanZ

      const local = new Cesium.Cartesian3(rx, ry, rz)
      const world = Cesium.Matrix4.multiplyByPoint(enu, local, new Cesium.Cartesian3())

      const a = 0.35 + Math.random() * 0.55
      const c = baseColor.withAlpha(a)
      const px = basePixelSize + Math.random() * 2.0

      points.add({
        position: world,
        color: c,
        pixelSize: px,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      })
    }

    _setOverlayEntry(_RUNTIME_KEYS.subsurfaceModel, { kind: 'primitive', primitive: points })
    try {
      viewer.scene?.requestRender?.()
    } catch (_) {
      // ignore
    }
    return true
  } catch (_) {
    return false
  }
}

function _entityRepresentativeCartesian(ent, time) {
  if (!ent) return null
  try {
    if (ent.position) {
      const p = ent.position.getValue?.(time) ?? ent.position
      if (p) return p
    }
  } catch (_) {
    // ignore
  }

  // Polygon centroid-ish: bounding sphere center of hierarchy positions.
  try {
    const h = ent?.polygon?.hierarchy
    if (h && typeof h.getValue === 'function') {
      const v = h.getValue(time)
      const pts = Array.isArray(v?.positions) ? v.positions : null
      if (pts && pts.length) {
        const bs = Cesium.BoundingSphere.fromPoints(pts)
        if (bs?.center) return bs.center
      }
    }
  } catch (_) {
    // ignore
  }

  // Polyline centroid-ish.
  try {
    const posProp = ent?.polyline?.positions
    if (posProp && typeof posProp.getValue === 'function') {
      const pts = posProp.getValue(time)
      if (Array.isArray(pts) && pts.length) {
        const bs = Cesium.BoundingSphere.fromPoints(pts)
        if (bs?.center) return bs.center
      }
    }
  } catch (_) {
    // ignore
  }

  return null
}

function _sceneCartesianToWindow(scene, cartesian, result) {
  if (!scene || !cartesian) return null
  const st = Cesium.SceneTransforms
  const fn = (st && (st.worldToWindowCoordinates || st.wgs84ToWindowCoordinates)) || null
  if (typeof fn !== 'function') return null
  try {
    return fn(scene, cartesian, result)
  } catch (_) {
    return null
  }
}

function _stopVectorSwipeHook(viewer) {
  try {
    if (_vectorSwipeUnsub) {
      _vectorSwipeUnsub()
      _vectorSwipeUnsub = null
    }
  } catch (_) {
    _vectorSwipeUnsub = null
  }

  // Restore entity.show so ds.show remains the single source of truth.
  try {
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'geojson' || !entry.dataSource) continue
      for (const ent of entry.dataSource.entities.values) ent.show = true
    }
  } catch (_) {
    // ignore
  }

  try {
    viewer?.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
}

function _ensureVectorSwipeHook(viewer) {
  if (!viewer) return
  if (_vectorSwipeUnsub) return

  const scene = viewer.scene
  if (!scene) return

  // Fallback for Entity/DataSource overlays: approximate a vertical "cut" by
  // hiding entities based on their screen-space centroid relative to splitPosition.
  const scratchWin = new Cesium.Cartesian2()
  const cb = () => {
    const enabled = !!swipeEnabled.value
    if (!enabled) return

    const t = viewer.clock?.currentTime || Cesium.JulianDate.now()
    const pos = Math.max(0, Math.min(1, Number(swipePosition.value) || 0.5))
    const canvas = scene.canvas
    const w = Number(canvas?.clientWidth || canvas?.width || 0)
    if (!w) return
    const splitX = pos * w

    // Patch 0303: left stays as clean basemap; all GeoJSON overlays are treated
    // as RIGHT-side overlays (hide anything left of split).
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'geojson' || !entry.dataSource) continue
      if (!entry.dataSource.show) continue
      for (const ent of entry.dataSource.entities.values) {
        const c = _entityRepresentativeCartesian(ent, t)
        if (!c) continue
        const win = _sceneCartesianToWindow(scene, c, scratchWin)
        if (!win) continue
        const x = Number(win.x)
        if (!Number.isFinite(x)) continue
        ent.show = x >= splitX
      }
    }
  }

  try {
    scene.preRender.addEventListener(cb)
    _vectorSwipeUnsub = () => {
      try {
        scene.preRender.removeEventListener(cb)
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    _vectorSwipeUnsub = null
  }
}

function _applyVectorSwipeState(viewer, enabled) {
  if (!viewer) return
  if (!enabled) {
    _stopVectorSwipeHook(viewer)
    return
  }
  _ensureVectorSwipeHook(viewer)
}

function _viewerAlive() {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return null
  try {
    if (typeof viewer.isDestroyed === 'function' && viewer.isDestroyed()) return null
  } catch (_) {
    // ignore
  }
  return viewer
}

const _RUNTIME_KEYS = Object.freeze({
  tileset: 'phase3-tileset',
  czml: 'phase3-czml',
  extruded: 'phase3-extruded',
  water: 'demo7-water',
  subsurfaceModel: 'demo12-subsurface-model',
  deformation: 'demo8-deformation',
  bivariate: 'demo10-bivariate',
})

// Global Standby default: start from a deep-space view.
// Local context dives are triggered by explicit tool calls (e.g., camera_fly_to / fly_to).
const initialLocation = computed(() => ({ lon: 105.0, lat: 35.0, height: 20000000.0 }))

function flyToScenario() {
  const cam = props.scenario?.camera
  if (!cam) return
  try {
    const d = Number(cam.duration_s)
    const duration = Number.isFinite(d) && d > 0 ? d : 3.8
    cesiumViewer.value?.flyTo?.(cam, duration)
  } catch (_) {
    // ignore
  }
}

function onViewerReady(viewer) {
  cesiumViewerInstance.value = viewer || null
  _disableDefaultDoubleClick(viewer)
  emit('viewer-ready', viewer)
  try {
    void applyLayersAsync(props.layers)
  } catch (_) {
    // ignore
  }
}

function startGlobalStandby() {
  try {
    cesiumViewer.value?.startGlobalRotation?.()
  } catch (_) {
    // ignore
  }
}

function stopGlobalStandby() {
  try {
    cesiumViewer.value?.stopGlobalRotation?.()
  } catch (_) {
    // ignore
  }
}

function flyToLocation(location, duration = 3.8) {
  try {
    cesiumViewer.value?.flyTo?.(location, duration)
  } catch (_) {
    // ignore
  }
}

function _scenarioBackend() {
  const b = props.scenario?.backend || {}
  return {
    mode: String(b.mode || '').trim(),
    location: String(b.location || '').trim(),
  }
}

function _getLayerParam(l, key, fallback) {
  try {
    const v = l?.params?.[key]
    return v === undefined ? fallback : v
  } catch (_) {
    return fallback
  }
}

function _clamp01(x, fallback = 1) {
  const n = Number(x)
  if (!Number.isFinite(n)) return fallback
  return Math.max(0, Math.min(1, n))
}

function _overlayEntry(id) {
  const map = overlayHandles.value
  return map.get(id) || null
}

function _setOverlayEntry(id, entry) {
  overlayHandles.value.set(id, entry)
}

function _removeOverlayEntry(id) {
  const map = overlayHandles.value
  const entry = map.get(id)
  if (!entry) return
  const viewer = cesiumViewerInstance.value
  try {
    if (entry.kind === 'imagery' && entry.layer && viewer) {
      viewer.imageryLayers.remove(entry.layer, true)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'primitive' && entry.primitive && viewer) {
      viewer.scene?.primitives?.remove?.(entry.primitive)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'geojson' && entry.dataSource && viewer) {
      viewer.dataSources.remove(entry.dataSource, true)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'tileset' && entry.tileset && viewer) {
      viewer.scene?.primitives?.remove?.(entry.tileset)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'czml' && entry.dataSource && viewer) {
      viewer.dataSources.remove(entry.dataSource, true)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'entity' && entry.entity && viewer) {
      viewer.entities.remove(entry.entity)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'shader' && typeof entry.cleanup === 'function') {
      entry.cleanup()
    }
  } catch (_) {
    // ignore
  }
  map.delete(id)
}

async function enable3DTerrain(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const terrainKey = String(options?.terrain || 'cesium_world_terrain').trim().toLowerCase()
  if (!terrainKey) return false

  try {
    if (terrainKey === 'cesium_world_terrain') {
      if (typeof Cesium.createWorldTerrainAsync === 'function') {
        viewer.terrainProvider = await Cesium.createWorldTerrainAsync()
      } else if (typeof Cesium.createWorldTerrain === 'function') {
        viewer.terrainProvider = Cesium.createWorldTerrain()
      }
      try {
        if (viewer.scene?.globe) viewer.scene.globe.depthTestAgainstTerrain = true
      } catch (_) {
        // ignore
      }
      return true
    }
  } catch (_) {
    // ignore
  }

  return false
}

async function addCesium3DTiles(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const url = String(options?.url || '').trim()
  const ionAssetIdRaw = options?.ion_asset_id
  const ionAssetId = Number(ionAssetIdRaw)

  _removeOverlayEntry(_RUNTIME_KEYS.tileset)

  let resourceUrl = url
  try {
    if (!resourceUrl && Number.isFinite(ionAssetId) && ionAssetId > 0 && Cesium?.IonResource?.fromAssetId) {
      resourceUrl = await Cesium.IonResource.fromAssetId(ionAssetId)
    }
  } catch (_) {
    // ignore
  }

  if (!resourceUrl) return false

  try {
    const tileset = await Cesium.Cesium3DTileset.fromUrl(resourceUrl)
    viewer.scene.primitives.add(tileset)
    _setOverlayEntry(_RUNTIME_KEYS.tileset, { kind: 'tileset', tileset })
    return true
  } catch (_) {
    return false
  }
}

function setSceneMode(mode = 'day') {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const m = String(mode || '').trim().toLowerCase()
  const isNight = m === 'night'

  try {
    // 0303 patch: do NOT use Cesium physical lighting for the "night" demo.
    // We want a stylized cyber-dark basemap, otherwise backfaces can become pure black.
    if (viewer.scene?.globe) viewer.scene.globe.enableLighting = false
  } catch (_) {
    // ignore
  }

  // Demo 11 visual impact: tune base imagery so AI overlays/CZML pop.
  // Reversible: we snapshot the current layer params and restore when leaving night.
  try {
    if (!isNight && typeof _nightRestore === 'function') {
      _nightRestore()
      _nightRestore = null
    }
  } catch (_) {
    _nightRestore = null
  }

  try {
    if (isNight && !_nightRestore && viewer.imageryLayers?.length) {
      const layers = viewer.imageryLayers
      const snapshot = []
      for (let i = 0; i < layers.length; i += 1) {
        const layer = layers.get(i)
        if (!layer) continue
        snapshot.push({
          layer,
          brightness: layer.brightness,
          contrast: layer.contrast,
          hue: layer.hue,
          saturation: layer.saturation,
          gamma: layer.gamma,
        })
        try {
          layer.brightness = 0.22
          layer.contrast = 1.7
          layer.saturation = 0.65
          layer.hue = -0.12
          layer.gamma = 0.85
        } catch (_) {
          // ignore
        }
      }
      _nightRestore = () => {
        for (const s of snapshot) {
          try {
            if (!s?.layer) continue
            s.layer.brightness = s.brightness
            s.layer.contrast = s.contrast
            s.layer.hue = s.hue
            s.layer.saturation = s.saturation
            s.layer.gamma = s.gamma
          } catch (_) {
            // ignore
          }
        }
      }
    }
  } catch (_) {
    // ignore
  }

  return true
}

function resetSceneState() {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  // Cancel any in-flight async layer application.
  try {
    applyToken.value += 1
  } catch (_) {
    // ignore
  }

  // Stop compute/overlays first to avoid background GPU work.
  try {
    destroyWebGpuSandbox()
  } catch (_) {
    // ignore
  }

  // Restore stylized night filter if active.
  try {
    if (typeof _nightRestore === 'function') _nightRestore()
  } catch (_) {
    // ignore
  }
  _nightRestore = null

  // Exit subsurface mode and restore camera collision defaults.
  try {
    disableSubsurfaceMode()
  } catch (_) {
    // ignore
  }

  // Remove all runtime overlays (tileset/czml/extruded/water/subsurface/deformation and any others).
  try {
    const keys = Array.from(overlayHandles.value.keys())
    for (const k of keys) _removeOverlayEntry(k)
  } catch (_) {
    // ignore
  }

  // Stop swipe hooks (preRender callbacks) if any.
  try {
    _stopVectorSwipeHook(viewer)
  } catch (_) {
    // ignore
  }

  // Safety defaults: opaque globe, no physical lighting, sane clock.
  try {
    if (viewer.scene?.globe) viewer.scene.globe.enableLighting = false
  } catch (_) {
    // ignore
  }
  try {
    setGlobeTransparency(1.0)
  } catch (_) {
    // ignore
  }
  try {
    if (viewer.clock) {
      viewer.clock.shouldAnimate = false
      viewer.clock.multiplier = 1.0
      if (Cesium?.JulianDate?.now) viewer.clock.currentTime = Cesium.JulianDate.now()
    }
  } catch (_) {
    // ignore
  }

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
  return true
}

async function playCzmlAnimation(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const czmlUrl = String(options?.czml_url || '').trim()
  const czml = Array.isArray(options?.czml) ? options.czml : null
  const speed = Number(options?.speed)

  _removeOverlayEntry(_RUNTIME_KEYS.czml)

  try {
    const ds = czmlUrl
      ? await Cesium.CzmlDataSource.load(czmlUrl)
      : await Cesium.CzmlDataSource.load(czml || [])

    viewer.dataSources.add(ds)
    _setOverlayEntry(_RUNTIME_KEYS.czml, { kind: 'czml', dataSource: ds })

    try {
      viewer.clock.multiplier = Number.isFinite(speed) && speed > 0 ? speed : 1.0
      viewer.clock.shouldAnimate = true
    } catch (_) {
      // ignore
    }

    return true
  } catch (_) {
    return false
  }
}

function setGlobeTransparency(alpha = 1.0) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const a = Number(alpha)
  if (!Number.isFinite(a)) return false
  const clamped = Math.max(0, Math.min(1, a))

  try {
    const globe = viewer.scene?.globe
    if (!globe) return false
    globe.translucency.enabled = clamped < 0.999
    globe.translucency.frontFaceAlpha = clamped
    globe.translucency.backFaceAlpha = clamped
    return true
  } catch (_) {
    return false
  }
}

async function addExtrudedPolygons(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const geojson = options?.geojson
  if (!geojson) return false

  const height = Number(options?.height)
  const heightProperty = String(options?.height_property || '').trim()
  const heightScaleRaw = Number(options?.height_scale)
  const heightScale = Number.isFinite(heightScaleRaw) ? heightScaleRaw : 1.0
  const heightMinRaw = Number(options?.height_min)
  const heightMaxRaw = Number(options?.height_max)
  const heightMin = Number.isFinite(heightMinRaw) ? heightMinRaw : 0.0
  const heightMax = Number.isFinite(heightMaxRaw) ? heightMaxRaw : Number.POSITIVE_INFINITY
  const opacity = Number(options?.opacity)
  const css = String(options?.color || '#00F0FF').trim() || '#00F0FF'
  const a = Number.isFinite(opacity) ? Math.max(0.05, Math.min(1, opacity)) : 0.55
  const fill = Cesium.Color.fromCssColorString(css).withAlpha(a)
  const stroke = fill.withAlpha(Math.min(0.9, a + 0.25))
  const baseFill = fill.withAlpha(Math.max(0.12, a * 0.25))

  _removeOverlayEntry(_RUNTIME_KEYS.extruded)

  try {
    const ds = await Cesium.GeoJsonDataSource.load(geojson, {
      clampToGround: true,
      // IMPORTANT: disable GeoJSON default stroke at load-time.
      // Otherwise Cesium may create terrain-clamped polygon outlines and emit
      // the one-time warning before we can set `polygon.outline = false`.
      stroke: Cesium.Color.TRANSPARENT,
      strokeWidth: 0,
      fill: baseFill,
    })

    for (const ent of ds.entities.values) {
      const poly = ent?.polygon
      if (!poly) continue
      try {
        if (Number.isFinite(height)) {
          poly.extrudedHeight = height
        } else if (heightProperty) {
          const props = ent?.properties
          const v = props?.[heightProperty]
          const now = Cesium.JulianDate.now()
          const raw = (typeof v?.getValue === 'function') ? v.getValue(now) : v
          const num = Number(raw)
          if (Number.isFinite(num)) {
            const h = Math.max(heightMin, Math.min(heightMax, num * heightScale))
            poly.extrudedHeight = h
          }
        }
      } catch (_) {
        // ignore
      }
      try {
        poly.outline = false
        poly.material = fill
      } catch (_) {
        // ignore
      }

      // If the GeoJSON contains line features, re-apply a visible stroke.
      const line = ent?.polyline
      if (line) {
        try {
          line.clampToGround = true
          line.width = 2
          line.material = stroke
        } catch (_) {
          // ignore
        }
      }
    }

    viewer.dataSources.add(ds)
    _setOverlayEntry(_RUNTIME_KEYS.extruded, { kind: 'geojson', dataSource: ds, sig: `extruded:${Date.now()}` })
    return true
  } catch (_) {
    return false
  }
}

async function applyCustomShader(options = {}) {
  const viewer = _viewerAlive()
  if (!viewer) return false

  const kind = String(options?.kind || '').trim().toLowerCase() || 'custom'
  const params = (options && typeof options === 'object') ? options.params : null
  const roi = String(params?.roi || '').trim().toLowerCase()

  _removeOverlayEntry(_RUNTIME_KEYS.deformation)

  const roiCenters = {
    mauna_loa: { lat: 19.48, lon: -155.61, height: 2600 },
  }

  let lat = Number(params?.lat)
  let lon = Number(params?.lon)
  let height = Number(params?.height)

  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    const fromRoi = roi ? roiCenters[roi] : null
    if (fromRoi) {
      lat = fromRoi.lat
      lon = fromRoi.lon
      height = fromRoi.height
    }
  }

  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    const cam = props.scenario?.camera
    const camLat = Number(cam?.lat)
    const camLon = Number(cam?.lon)
    if (Number.isFinite(camLat) && Number.isFinite(camLon)) {
      lat = camLat
      lon = camLon
      if (!Number.isFinite(height)) height = 2200
    }
  }

  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false
  if (!Number.isFinite(height)) height = 2200

  const tilesetEntry = _overlayEntry(_RUNTIME_KEYS.tileset)
  const tileset = tilesetEntry?.kind === 'tileset' ? tilesetEntry.tileset : null

  if (tileset && Cesium?.CustomShader && Cesium?.UniformType && Cesium?.CustomShaderMode) {
    try {
      const shader = new Cesium.CustomShader({
        mode: Cesium.CustomShaderMode.MODIFY_MATERIAL,
        uniforms: {
          u_time: {
            type: Cesium.UniformType.FLOAT,
            value: 0.0,
          },
        },
        vertexShaderText: `
void vertexMain(VertexInput vsInput, inout czm_modelVertexOutput vsOutput) {
  float t = u_time * 0.65;
  vec3 n = normalize(vsInput.attributes.normalMC);
  vec3 p = vsInput.attributes.positionMC;
  float r = length(p.xy) * 0.00015;
  float wave = sin(r * 10.0 - t) * 18.0;
  vsOutput.positionMC += n * wave;
}
        `.trim(),
        fragmentShaderText: `
void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
  float h = clamp(fsInput.attributes.positionMC.z * 0.001, 0.0, 1.0);
  vec3 cool = vec3(0.0, 0.95, 1.0);
  vec3 heat = vec3(1.0, 0.35, 0.05);
  material.diffuse = mix(cool, heat, h);
  material.alpha = 0.92;
}
        `.trim(),
      })

      tileset.customShader = shader

      const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
      const onPreRender = () => {
        try {
          const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
          shader.uniforms.u_time.value = (now - t0) / 1000.0
        } catch (_) {
          // ignore
        }
      }

      try {
        viewer.scene?.preRender?.addEventListener?.(onPreRender)
      } catch (_) {
        // ignore
      }

      _setOverlayEntry(_RUNTIME_KEYS.deformation, {
        kind: 'shader',
        cleanup: () => {
          try {
            viewer.scene?.preRender?.removeEventListener?.(onPreRender)
          } catch (_) {
            // ignore
          }
          try {
            if (tileset.customShader === shader) tileset.customShader = undefined
          } catch (_) {
            // ignore
          }
        },
      })

      try {
        viewer.scene?.requestRender?.()
      } catch (_) {
        // ignore
      }

      return true
    } catch (_) {
      // Fall back to entity overlay.
    }
  }

  // Resource-free fallback: pulsing deformation bulb + heat ring.
  try {
    const pos = Cesium.Cartesian3.fromDegrees(lon, lat, height)
    const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
    const base = (kind === 'insar_lst') ? Cesium.Color.fromCssColorString('#FF4D00') : Cesium.Color.fromCssColorString('#00F0FF')

    const alphaProp = new Cesium.CallbackProperty(() => {
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
      const t = (now - t0) / 1000.0
      const pulse = 0.55 + 0.25 * Math.sin(t * 1.25)
      return base.withAlpha(Math.max(0.08, Math.min(0.95, pulse)))
    }, false)

    const radiiProp = new Cesium.CallbackProperty(() => {
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
      const t = (now - t0) / 1000.0
      const k = 1.0 + 0.12 * Math.sin(t * 1.25)
      return new Cesium.Cartesian3(9000.0 * k, 9000.0 * k, 5200.0 * (1.0 + 0.18 * Math.sin(t * 0.9)))
    }, false)

    const entity = viewer.entities.add({
      position: pos,
      ellipsoid: {
        radii: radiiProp,
        material: new Cesium.ColorMaterialProperty(alphaProp),
        outline: true,
        outlineColor: base.withAlpha(0.85),
      },
      label: {
        text: roi ? `Demo 8 ${roi.toUpperCase()}  (${kind})` : `Demo 8 (${kind})`,
        font: '13pt ui-monospace, monospace',
        fillColor: Cesium.Color.WHITE,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        pixelOffset: new Cesium.Cartesian2(0, -26),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    _setOverlayEntry(_RUNTIME_KEYS.deformation, { kind: 'entity', entity })
    return true
  } catch (_) {
    return false
  }
}

async function addWaterPolygon(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const arr = Array.isArray(options?.positions_degrees) ? options.positions_degrees : null
  if (!arr || arr.length < 6) return false

  const css = String(options?.color || '#00F0FF').trim() || '#00F0FF'
  const opacityRaw = Number(options?.opacity)
  const opacity = Number.isFinite(opacityRaw) ? Math.max(0.05, Math.min(1, opacityRaw)) : 0.45
  const labelText = String(options?.label || '').trim()
  const waveSpeedRaw = Number(options?.wave_speed)
  const waveSpeed = Number.isFinite(waveSpeedRaw) ? Math.max(0.05, Math.min(10, waveSpeedRaw)) : 1.2

  _removeOverlayEntry(_RUNTIME_KEYS.water)

  try {
    const positions = Cesium.Cartesian3.fromDegreesArray(arr.map((x) => Number(x)))
    const base = Cesium.Color.fromCssColorString(css)
    const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()

    const colorProp = new Cesium.CallbackProperty(() => {
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()
      const t = (now - t0) / 1000.0
      const pulse = 0.65 + 0.25 * Math.sin(t * waveSpeed)
      return base.withAlpha(Math.max(0.05, Math.min(1.0, opacity * pulse)))
    }, false)

    const entity = viewer.entities.add({
      polygon: {
        hierarchy: positions,
        material: new Cesium.ColorMaterialProperty(colorProp),
        outline: true,
        outlineColor: base.withAlpha(Math.min(0.9, opacity + 0.25)),
      },
      label: labelText
        ? {
            text: labelText,
            font: '13pt ui-monospace, monospace',
            fillColor: Cesium.Color.WHITE,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            pixelOffset: new Cesium.Cartesian2(0, -18),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          }
        : undefined,
    })

    _setOverlayEntry(_RUNTIME_KEYS.water, { kind: 'entity', entity })
    return true
  } catch (_) {
    return false
  }
}

async function renderBivariateGridOverlay(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const title = String(options?.title || '').trim()
  const data = (options && typeof options === 'object') ? (options.data ?? options) : null
  if (!data || typeof data !== 'object') return false

  const bounds = data?.bounds || {}
  const west = Number(bounds?.west)
  const east = Number(bounds?.east)
  const south = Number(bounds?.south)
  const north = Number(bounds?.north)
  if (![west, east, south, north].every((n) => Number.isFinite(n))) return false
  if (!(east > west && north > south)) return false

  const dims = data?.dims || {}
  const colsRaw = Number(dims?.cols)
  const rowsRaw = Number(dims?.rows)
  const cols = Number.isFinite(colsRaw) ? Math.max(1, Math.min(80, Math.round(colsRaw))) : 10
  const rows = Number.isFinite(rowsRaw) ? Math.max(1, Math.min(80, Math.round(rowsRaw))) : 10

  const grid = Array.isArray(data?.grid) ? data.grid : []
  if (!grid.length) return false

  const opacityRaw = Number(data?.opacity)
  const opacity = Number.isFinite(opacityRaw) ? Math.max(0.05, Math.min(0.95, opacityRaw)) : 0.62

  _removeOverlayEntry(_RUNTIME_KEYS.bivariate)

  const dx = (east - west) / Math.max(1, cols)
  const dy = (north - south) / Math.max(1, rows)

  try {
    const ds = new Cesium.CustomDataSource(_RUNTIME_KEYS.bivariate)

    for (const cell of grid) {
      const i = Number(cell?.i)
      const j = Number(cell?.j)
      if (!Number.isFinite(i) || !Number.isFinite(j)) continue
      if (i < 0 || i >= cols || j < 0 || j >= rows) continue

      const css = String(cell?.color || '').trim() || '#7AAED6'
      let color = null
      try {
        color = Cesium.Color.fromCssColorString(css).withAlpha(opacity)
      } catch (_) {
        color = Cesium.Color.fromCssColorString('#7AAED6').withAlpha(opacity)
      }

      const w = west + i * dx
      const e = west + (i + 1) * dx
      const s = south + j * dy
      const n = south + (j + 1) * dy
      if (!(e > w && n > s)) continue

      ds.entities.add({
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(w, s, e, n),
          material: color,
          outline: false,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
      })
    }

    const centerLon = (west + east) * 0.5
    const centerLat = (south + north) * 0.5
    ds.entities.add({
      position: Cesium.Cartesian3.fromDegrees(centerLon, centerLat, 0),
      label: {
        text: title || 'Bivariate Grid',
        font: '13pt ui-monospace, monospace',
        fillColor: Cesium.Color.WHITE,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        pixelOffset: new Cesium.Cartesian2(0, -26),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })

    viewer.dataSources.add(ds)
    _setOverlayEntry(_RUNTIME_KEYS.bivariate, { kind: 'czml', dataSource: ds, sig: `bivariate:${Date.now()}` })

    try {
      viewer.scene?.requestRender?.()
    } catch (_) {
      // ignore
    }
    return true
  } catch (_) {
    return false
  }
}

async function _ensureAiVector({ enabled, opacity, geojson, token, color }) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const id = 'ai-vector'
  const sig = `ai-vector:${JSON.stringify(geojson || null)}:${String(color || '')}`
  const existing = _overlayEntry(id)

  if (existing?.kind === 'geojson' && existing.sig === sig) {
    try {
      existing.dataSource.show = !!enabled
    } catch (_) {
      // ignore
    }
    // opacity update is best-effort (some entity materials may not exist).
    try {
      const a = _clamp01(opacity, 0.9)
      const css = String(color || '#00F0FF').trim() || '#00F0FF'
      const c = Cesium.Color.fromCssColorString(css).withAlpha(Math.max(0.15, a))
      for (const ent of existing.dataSource.entities.values) {
        if (ent?.polyline?.material) ent.polyline.material = c
        if (ent?.polygon) {
          if (ent.polygon.material) ent.polygon.material = c.withAlpha(Math.max(0.10, a * 0.35))
          ent.polygon.outline = false
        }
        if (ent?.point?.color) ent.point.color = c
      }
    } catch (_) {
      // ignore
    }
    return
  }

  _removeOverlayEntry(id)
  if (!geojson) return

  try {
    const a = _clamp01(opacity, 0.9)
    const css = String(color || '#00F0FF').trim() || '#00F0FF'
    const stroke = Cesium.Color.fromCssColorString(css).withAlpha(Math.max(0.15, a))
    const fill = stroke.withAlpha(Math.max(0.10, a * 0.35))

    const ds = await Cesium.GeoJsonDataSource.load(geojson, {
      clampToGround: true,
      // IMPORTANT: disable GeoJSON default stroke at load-time.
      // Otherwise Cesium may create terrain-clamped polygon outlines and emit
      // the one-time warning before we can set `polygon.outline = false`.
      stroke: Cesium.Color.TRANSPARENT,
      strokeWidth: 0,
      fill,
    })
    if (token !== applyToken.value) return

    // Re-apply styling post-load so polylines remain visible while polygon
    // outlines stay disabled on terrain.
    try {
      for (const ent of ds.entities.values) {
        if (ent?.polyline) {
          try {
            ent.polyline.clampToGround = true
            ent.polyline.width = 2
            ent.polyline.material = stroke
          } catch (_) {
            // ignore
          }
        }
        if (ent?.polygon) {
          try {
            ent.polygon.outline = false
            ent.polygon.material = fill
          } catch (_) {
            // ignore
          }
        }
        if (ent?.point) {
          try {
            ent.point.color = stroke
          } catch (_) {
            // ignore
          }
        }
      }
    } catch (_) {
      // ignore
    }
    try {
      ds.show = !!enabled
    } catch (_) {
      // ignore
    }
    viewer.dataSources.add(ds)
    _setOverlayEntry(id, { kind: 'geojson', dataSource: ds, sig })
  } catch (_) {
    // ignore
  }
}

async function _ensureGeoJsonBoundaries({ enabled, opacity, token }) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const { mode, location } = _scenarioBackend()
  if (!location) return

  const id = 'boundaries'
  const sig = `geojson:${location}:${mode}`

  const existing = _overlayEntry(id)
  if (existing?.kind === 'geojson' && existing.sig === sig) {
    try {
      existing.dataSource.show = !!enabled
    } catch (_) {
      // ignore
    }
    try {
      const a = _clamp01(opacity, 0.9)
      const outlineAlpha = Math.max(0.15, a)

      // IMPORTANT:
      // Cesium warns that polygon outlines are unsupported when clamped to terrain.
      // We keep polygon fill transparent, disable polygon outlines, and draw a
      // separate clamped polyline as the visible boundary.
      const t = Cesium.JulianDate.now()
      for (const ent of existing.dataSource.entities.values) {
        const poly = ent?.polygon
        if (poly) {
          poly.material = Cesium.Color.TRANSPARENT
          poly.outline = false

          // Ensure we have a matching outline polyline.
          try {
            const props = ent?.properties
            const hasLine = !!(props && (props.__oneearth_has_outline?.getValue?.() ?? props.__oneearth_has_outline))
            if (!hasLine && poly?.hierarchy) {
              const h = poly.hierarchy.getValue(t)
              const positions = Array.isArray(h?.positions) ? h.positions : null
              if (positions && positions.length >= 3) {
                const closed = positions[0] === positions[positions.length - 1]
                const linePositions = closed ? positions : [...positions, positions[0]]
                existing.dataSource.entities.add({
                  name: `${ent?.name || 'Boundary'} (outline)`,
                  polyline: {
                    positions: linePositions,
                    clampToGround: true,
                    width: 2,
                    material: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(outlineAlpha),
                  },
                  properties: {
                    __oneearth_outline: true,
                    __oneearth_for: String(ent?.id || ''),
                  },
                })

                try {
                  if (props && typeof props.addProperty === 'function') {
                    props.addProperty('__oneearth_has_outline')
                    props.__oneearth_has_outline = true
                  } else if (props) {
                    props.__oneearth_has_outline = true
                  }
                } catch (_) {
                  // ignore
                }
              }
            }
          } catch (_) {
            // ignore
          }
        }

        // Update any existing outline polylines.
        const line = ent?.polyline
        if (line && line.material) {
          try {
            const isOutline = !!(ent?.properties && (ent.properties.__oneearth_outline?.getValue?.() ?? ent.properties.__oneearth_outline))
            if (isOutline) {
              line.material = Cesium.Color.fromCssColorString('#00F0FF').withAlpha(outlineAlpha)
            }
          } catch (_) {
            // ignore
          }
        }
      }
    } catch (_) {
      // ignore
    }
    return
  }

  // Replace any existing stub/old DS.
  _removeOverlayEntry(id)

  const url = `/api/geojson/boundaries?location=${encodeURIComponent(location)}${mode ? `&mode=${encodeURIComponent(mode)}` : ''}`

  try {
    const ds = await Cesium.GeoJsonDataSource.load(url, {
      clampToGround: true,
      // IMPORTANT: disable GeoJSON default stroke at load-time.
      // Otherwise Cesium will create terrain-clamped polygon outlines and emit
      // the one-time warning before we can set `polygon.outline = false`.
      stroke: Cesium.Color.TRANSPARENT,
      strokeWidth: 0,
      fill: Cesium.Color.TRANSPARENT,
    })
    if (token !== applyToken.value) return

    const a = _clamp01(opacity, 0.9)
    const outlineAlpha = Math.max(0.15, a)
    const t = Cesium.JulianDate.now()

    try {
      for (const ent of ds.entities.values) {
        const poly = ent?.polygon
        if (poly) {
          // Keep fill transparent. Disable polygon outlines to avoid the Cesium warning.
          poly.material = Cesium.Color.TRANSPARENT
          poly.outline = false

          // Derive a boundary polyline from the polygon hierarchy.
          try {
            const h = poly?.hierarchy?.getValue?.(t)
            const positions = Array.isArray(h?.positions) ? h.positions : null
            if (positions && positions.length >= 3) {
              const closed = positions[0] === positions[positions.length - 1]
              const linePositions = closed ? positions : [...positions, positions[0]]
              ds.entities.add({
                name: `${ent?.name || 'Boundary'} (outline)`,
                polyline: {
                  positions: linePositions,
                  clampToGround: true,
                  width: 2,
                  material: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(outlineAlpha),
                },
                properties: {
                  __oneearth_outline: true,
                  __oneearth_for: String(ent?.id || ''),
                },
              })

              // Compute a centroid-ish label position.
              try {
                let sumLat = 0
                let sumLon = 0
                let n = 0
                for (const p of positions) {
                  const c = Cesium.Cartographic.fromCartesian(p)
                  sumLat += c.latitude
                  sumLon += c.longitude
                  n += 1
                }
                if (n > 0) {
                  const lat = sumLat / n
                  const lon = sumLon / n
                  ent.position = Cesium.Cartesian3.fromRadians(lon, lat, 0)
                }
              } catch (_) {
                // ignore
              }
            }
          } catch (_) {
            // ignore
          }

          // Mark so the update-path can avoid duplicating lines.
          try {
            const props = ent?.properties
            if (props && typeof props.addProperty === 'function') {
              props.addProperty('__oneearth_has_outline')
              props.__oneearth_has_outline = true
            } else if (props) {
              props.__oneearth_has_outline = true
            }
          } catch (_) {
            // ignore
          }
        }

        // Optional label.
        try {
          const name = String(ent?.properties?.name?.getValue?.() || ent?.properties?.name || '').trim()
          if (name) {
            ent.label = new Cesium.LabelGraphics({
              text: name,
              font: '12px sans-serif',
              fillColor: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(0.85),
              outlineColor: Cesium.Color.BLACK.withAlpha(0.55),
              outlineWidth: 2,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              pixelOffset: new Cesium.Cartesian2(0, -14),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            })
          }
        } catch (_) {
          // ignore
        }
      }
    } catch (_) {
      // ignore
    }

    ds.show = !!enabled
    viewer.dataSources.add(ds)
    _setOverlayEntry(id, { kind: 'geojson', dataSource: ds, sig })
  } catch (_) {
    // Best-effort only
  }
}

async function _ensureImageryLayerForId({ id, enabled, opacity, options, token }) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return
  if (!id) return

  const { mode, location } = _scenarioBackend()
  if (!mode || !location) return

  if (!enabled) {
    const e = _overlayEntry(id)
    if (e?.kind === 'imagery' && e.layer) {
      try {
        e.layer.show = false
      } catch (_) {
        // ignore
      }
    }
    return
  }

  const opts = options && typeof options === 'object' ? options : {}
  // AI imagery overlay: allow a direct tile template URL from tool-calling events.
  if (id === 'ai-imagery') {
    const direct = String((opts && (opts.tile_url || opts.url)) || '').trim()
    const sig = `ai-imagery:${direct}:${JSON.stringify(opts)}`
    const existing = _overlayEntry(id)

    if (existing?.kind === 'imagery' && existing.sig === sig) {
      try {
        existing.layer.show = true
        existing.layer.alpha = _clamp01(opacity, 0.65)
      } catch (_) {
        // ignore
      }
      return
    }

    _removeOverlayEntry(id)
    if (!direct) return
    if (token !== applyToken.value) return

    try {
      const provider = new Cesium.UrlTemplateImageryProvider({
        url: direct,
        tilingScheme: new Cesium.WebMercatorTilingScheme(),
        maximumLevel: 24,
        enablePickFeatures: false,
      })
      const layer = viewer.imageryLayers.addImageryProvider(provider)
      try {
        layer.__oneearthOverlay = true
      } catch (_) {
        // ignore
      }
      layer.alpha = _clamp01(opacity, 0.65)
      layer.show = !!enabled
      _setOverlayEntry(id, { kind: 'imagery', layer, sig })
    } catch (_) {
      // ignore
    }
    return
  }

  const sig = `${id}:${mode}:${location}:${JSON.stringify(opts)}`
  const existing = _overlayEntry(id)

  if (existing?.kind === 'imagery' && existing.sig === sig) {
    try {
      existing.layer.show = true
      existing.layer.alpha = _clamp01(opacity, 0.8)
    } catch (_) {
      // ignore
    }
    return
  }

  // Fetch tile URL from backend (same-origin /api/tiles proxy).
  let tileUrl = ''
  try {
    const resp = await apiService.getLayer(mode, location, opts)
    tileUrl = String(resp?.tile_url || '').trim()
  } catch (_) {
    tileUrl = ''
  }
  if (!tileUrl) return
  if (token !== applyToken.value) return

  // Replace existing layer if sig changed.
  _removeOverlayEntry(id)

  try {
    const provider = new Cesium.UrlTemplateImageryProvider({
      url: tileUrl,
      tilingScheme: new Cesium.WebMercatorTilingScheme(),
      // Allow deeper zoom when the camera is close to ground.
      maximumLevel: 24,
      enablePickFeatures: false,
    })

    const layer = viewer.imageryLayers.addImageryProvider(provider)
    // Mark as an externally-managed overlay (used by CesiumViewer to avoid
    // photorealistic 3D tileset occluding Workbench imagery overlays).
    try {
      layer.__oneearthOverlay = true
    } catch (_) {
      // ignore
    }
    layer.alpha = _clamp01(opacity, 0.8)
    layer.show = !!enabled
    _setOverlayEntry(id, { kind: 'imagery', layer, sig })
  } catch (_) {
    // ignore
  }
}

function _reorderImageryLayers(layers) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return
  const arr = Array.isArray(layers) ? layers : []
  const imageryIds = arr
    .map((l) => String(l?.id || '').trim())
    .filter((id) => id && id !== 'boundaries')
    .filter((id) => {
      const e = _overlayEntry(id)
      return e?.kind === 'imagery' && !!e?.layer
    })

  // Treat LayerTree list order as TOP -> BOTTOM.
  // Raise from bottom to top so the first item ends on top.
  for (const id of imageryIds.slice().reverse()) {
    const e = _overlayEntry(id)
    if (e?.kind !== 'imagery' || !e.layer) continue
    try {
      viewer.imageryLayers.raiseToTop(e.layer)
    } catch (_) {
      // ignore
    }
  }
}

function _resetSwipeDirections(viewer) {
  if (!viewer) return
  const SD = Cesium.SplitDirection || Cesium.ImagerySplitDirection
  if (!SD) return
  try {
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'imagery' || !entry?.layer) continue
      try {
        entry.layer.splitDirection = SD.NONE
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }
}

function _applySwipeState(viewer) {
  if (!viewer) return
  const enabled = !!swipeEnabled.value
  const pos = Math.max(0, Math.min(1, Number(swipePosition.value) || 0.5))

  try {
    viewer.scene.splitPosition = enabled ? pos : 0.5
  } catch (_) {
    // ignore
  }

  _resetSwipeDirections(viewer)

  // Apply vector swipe behavior (fallback for Entity/DataSource overlays).
  try {
    _applyVectorSwipeState(viewer, enabled)
  } catch (_) {
    // ignore
  }

  if (!enabled) return

  // Patch 0303: left stays clean basemap; force all overlay imagery layers to RIGHT.
  const SD = Cesium.SplitDirection || Cesium.ImagerySplitDirection
  if (!SD) return
  try {
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'imagery' || !entry?.layer) continue
      try {
        if (entry.layer.show !== false) entry.layer.splitDirection = SD.RIGHT
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }
}

function setSwipeMode(opts = {}) {
  swipeEnabled.value = !!opts?.enabled
  const pos = Number(opts?.position)
  if (Number.isFinite(pos)) swipePosition.value = Math.max(0, Math.min(1, pos))

  const viewer = _viewerAlive()
  _applySwipeState(viewer)
  try {
    viewer?.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
  return true
}

function setSwipePosition01(pos) {
  const n = Number(pos)
  if (!Number.isFinite(n)) return false
  swipePosition.value = Math.max(0, Math.min(1, n))
  const viewer = _viewerAlive()
  if (viewer && swipeEnabled.value) {
    _applySwipeState(viewer)
    try {
      viewer.scene?.requestRender?.()
    } catch (_) {
      // ignore
    }
  }
  return true
}

async function applyLayersAsync(layers) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const token = (applyToken.value += 1)
  const arr = Array.isArray(layers) ? layers : []

  const loadTasks = []

  // 1) Boundaries (GeoJSON)
  try {
    const l = arr.find((x) => String(x?.id || '') === 'boundaries')
    if (l) {
      const enabled = !!l?.enabled
      const opacity = _getLayerParam(l, 'opacity', 0.9)
      loadTasks.push(_ensureGeoJsonBoundaries({ enabled, opacity, token }))
    }
  } catch (_) {
    // ignore
  }

  // 2) AI vector overlay (GeoJSON)
  try {
    const l = arr.find((x) => String(x?.id || '') === 'ai-vector')
    if (l) {
      const enabled = !!l?.enabled
      const opacity = _getLayerParam(l, 'opacity', 0.9)
      const geojson = _getLayerParam(l, 'geojson', null)
      const color = String(_getLayerParam(l, 'color', '#00F0FF') || '').trim() || '#00F0FF'
      loadTasks.push(_ensureAiVector({ enabled, opacity, geojson, token, color }))
    }
  } catch (_) {
    // ignore
  }

  // 3) Imagery overlays (GEE tiles via backend proxy, plus ai-imagery direct URL)
  for (const l of arr) {
    const id = String(l?.id || '').trim()
    if (!id || id === 'boundaries') continue
    if (id === 'ai-vector') continue
    const enabled = !!l?.enabled
    const opacity = _getLayerParam(l, 'opacity', 0.8)

    const opts = {}
    if (id === 'ai-imagery') {
      const tileUrl = String(_getLayerParam(l, 'tile_url', '') || '').trim()
      if (tileUrl) opts.tile_url = tileUrl
    }
    if (id === 'anomaly-mask') {
      opts.variant = 'anomaly-mask'
      const thr = Number(_getLayerParam(l, 'threshold', 0.1))
      if (Number.isFinite(thr)) opts.threshold = thr
      const pal = String(_getLayerParam(l, 'palette', '') || '').trim()
      if (pal) opts.palette = pal
    } else {
      opts.variant = 'heatmap'
    }

    try {
      loadTasks.push(_ensureImageryLayerForId({ id, enabled, opacity, options: opts, token }))
    } catch (_) {
      // ignore
    }
  }

  try {
    await Promise.allSettled(loadTasks)
  } catch (_) {
    // ignore
  }

  if (token !== applyToken.value) return
  _reorderImageryLayers(arr)

  try {
    _applySwipeState(viewer)
  } catch (_) {
    // ignore
  }

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
}

watch(
  () => props.scenario?.id,
  () => {
    try {
      resetSceneState()
    } catch (_) {
      // ignore
    }
    try {
      void applyLayersAsync(props.layers)
    } catch (_) {
      // ignore
    }
  }
)

watch(
  () => props.layers,
  (v) => {
    try {
      void applyLayersAsync(v)
    } catch (_) {
      // ignore
    }
  },
  { deep: true }
)

defineExpose({
  flyToScenario,
  flyToLocation,
  startGlobalStandby,
  stopGlobalStandby,
  applyLayers: applyLayersAsync,
  enable3DTerrain,
  addCesium3DTiles,
  setSceneMode,
  playCzmlAnimation,
  setGlobeTransparency,
  applyCustomShader,
  addExtrudedPolygons,
  addWaterPolygon,
  renderBivariateGridOverlay,
  enableSubsurfaceMode,
  disableSubsurfaceMode,
  addSubsurfaceModel,
  executeDynamicWgsl,
  destroyWebGpuSandbox,
  setSwipeMode,
  setSwipePosition: setSwipePosition01,
  cesiumViewer,
  cesiumViewerInstance,
})
</script>

<style scoped>
.engine-router {
  position: absolute;
  inset: 0;
}

.engine-stack {
  position: relative;
  width: 100%;
  height: 100%;
  isolation: isolate;
}

.webgpu-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  z-index: 9999;
  transform: translateZ(0);
}

.pointer-events-none {
  pointer-events: none;
}

.engine-router :deep(.cesium-viewer-container) {
  width: 100%;
  height: 100%;
}
</style>
