<template>
  <div ref="container" class="three-twin w-full h-full" aria-label="Three Twin"></div>
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
import { ASTRO_AGENT_ACTION_TYPES, useAstroStore } from '../../../stores/astroStore.js'
import { disposeThreeEngine } from './threeDispose.js'
import { executeQuantumDive } from './quantumDive.js'
import { createBloomPipeline, updateBloomParams } from './threePostprocessing.js'
import { mapLayersToThreeParams } from './threeLayerMapping.js'

const emit = defineEmits(['ready'])

const props = defineProps({
  layers: { type: Array, default: () => [] },
})

const container = ref(null)
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

let macroMesh = null
let microRoot = null
let microSiMesh = null
let microOMesh = null
let microBondLines = null
let microMaterial = null
let microMaterialO = null

let _macroRedshiftTween = null
let _macroRedshiftShader = null
let _macroRedshiftPending = null
let _macroRedshiftMaxDepth = 42
let _macroRedshiftScale = 0

let _inpaintMesh = null
let _inpaintUniforms = null
let _inpaintActive = false
let _inpaintClickHandler = null
let _inpaintRadiusTween = null
let _inpaintTime = 0
const _inpaintRaycaster = new THREE.Raycaster()
const _inpaintMouse = new THREE.Vector2()

const MICRO_MAX_INSTANCES = 12000

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
  // Minimal procedural cosmic web using InstancedMesh.
  // Stage 2 Demo 1: add per-instance redshift attribute + uniform-driven stretch along +Z.
  const count = 100000
  const geometry = new THREE.SphereGeometry(0.02, 4, 4)

  const material = new THREE.MeshBasicMaterial({ color: 0xffffff })
  material.onBeforeCompile = (shader) => {
    shader.uniforms.u_redshift_scale = { value: Number(_macroRedshiftScale) || 0 }
    shader.uniforms.u_max_depth = { value: Number(_macroRedshiftMaxDepth) || 42 }

    shader.vertexShader = `attribute float aRedshift;\nuniform float u_redshift_scale;\nuniform float u_max_depth;\n${shader.vertexShader}`
    shader.vertexShader = shader.vertexShader.replace(
      'vec3 transformed = vec3( position );',
      'vec3 transformed = vec3( position );\ntransformed.z += aRedshift * u_redshift_scale * u_max_depth;'
    )

    _macroRedshiftShader = shader
  }
  material.needsUpdate = true

  const mesh = markRaw(new THREE.InstancedMesh(geometry, material, count))

  const redshift = new Float32Array(count)
  const tmp = new THREE.Object3D()
  for (let i = 0; i < count; i += 1) {
    const t = i / count
    const angle = t * Math.PI * 12
    const radius = 2 + t * 18
    tmp.position.set(Math.cos(angle) * radius, (t - 0.5) * 1.2, Math.sin(angle) * radius)
    tmp.updateMatrix()
    mesh.setMatrixAt(i, tmp.matrix)

    // Mock redshift values in [0,1]; later replaced by AION output.
    redshift[i] = Math.min(1, Math.max(0, t + (Math.sin(i * 0.015) * 0.08)))
  }

  try {
    mesh.geometry.setAttribute('aRedshift', new THREE.InstancedBufferAttribute(redshift, 1))
  } catch (_) {
    // ignore
  }

  scene.add(mesh)
  macroMesh = mesh

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
    }

    const inpaintMat = new THREE.ShaderMaterial({
      uniforms: _inpaintUniforms,
      transparent: true,
      depthWrite: false,
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
          gl_FragColor = vec4(mixed.rgb, alpha);
        }
      `,
    })

    const inpaintGeo = new THREE.PlaneGeometry(32, 18, 1, 1)
    _inpaintMesh = markRaw(new THREE.Mesh(inpaintGeo, inpaintMat))
    _inpaintMesh.visible = false
    _inpaintMesh.renderOrder = 999
    scene.add(_inpaintMesh)
  } catch (_) {
    _inpaintMesh = null
    _inpaintUniforms = null
  }
}

function _makeNebulaTexture({ w = 512, h = 512, palette = [], bloomBias = 0.5 } = {}) {
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(64, Math.floor(w))
  canvas.height = Math.max(64, Math.floor(h))
  const ctx = canvas.getContext('2d')

  const p = Array.isArray(palette) && palette.length ? palette : ['#050816', '#0b2a5a', '#7dd3fc', '#a78bfa']
  const g = ctx.createLinearGradient(0, 0, canvas.width, canvas.height)
  for (let i = 0; i < p.length; i += 1) {
    g.addColorStop(i / Math.max(1, p.length - 1), p[i])
  }
  ctx.fillStyle = g
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Add soft blobs + stars (procedural; no external assets).
  for (let i = 0; i < 140; i += 1) {
    const x = Math.random() * canvas.width
    const y = Math.random() * canvas.height
    const r = 18 + Math.random() * 140
    const a = (0.03 + Math.random() * 0.12) * (0.5 + bloomBias)
    const blob = ctx.createRadialGradient(x, y, 0, x, y, r)
    blob.addColorStop(0, `rgba(255,255,255,${a})`)
    blob.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.fillStyle = blob
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  for (let i = 0; i < 2600; i += 1) {
    const x = (Math.random() * canvas.width) | 0
    const y = (Math.random() * canvas.height) | 0
    const v = 180 + Math.random() * 75
    const a = (0.12 + Math.random() * 0.65) * (0.4 + bloomBias)
    ctx.fillStyle = `rgba(${v},${v},${v},${a})`
    ctx.fillRect(x, y, 1, 1)
  }

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
  if (_macroRedshiftShader?.uniforms?.u_redshift_scale) {
    _macroRedshiftShader.uniforms.u_redshift_scale.value = _macroRedshiftScale
    return
  }
  _macroRedshiftPending = _macroRedshiftScale
}

function _setMacroRedshiftMaxDepth(v) {
  const n = Number(v)
  _macroRedshiftMaxDepth = Number.isFinite(n) ? Math.max(1, Math.min(240, n)) : 42
  if (_macroRedshiftShader?.uniforms?.u_max_depth) {
    _macroRedshiftShader.uniforms.u_max_depth.value = _macroRedshiftMaxDepth
  }
}

async function _executeRedshiftBurst(payload = null) {
  if (!macroMesh) return

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

  const state = { v: _macroRedshiftScale }
  await new Promise((resolve) => {
    _macroRedshiftTween = gsap.to(state, {
      v: 1,
      duration: 1.35,
      ease: 'power2.out',
      onUpdate: () => _setMacroRedshiftScale(state.v),
      onComplete: resolve,
    })
  })

  try {
    astroStore.setGenerating(false)
  } catch (_) {
    // ignore
  }

  // Add a subtle bloom lift during the burst.
  try {
    const u = bloomPass
    if (u) {
      gsap.to(u, { strength: Math.min(2.2, (u.strength || 1.1) + 0.35), duration: 0.35, ease: 'power2.out' })
    }
  } catch (_) {
    // ignore
  }
}

function _startModalInpaint() {
  if (!_inpaintMesh || !_inpaintUniforms || !renderer || !camera) return

  _inpaintActive = true
  _inpaintMesh.visible = true
  _inpaintUniforms.u_enabled.value = 1.0
  _inpaintUniforms.u_radius.value = 0.0

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
          camera.lookAt(0, 0, 0)
        } catch (_) {
          // ignore
        }
      },
      onComplete: resolve,
    })
  })
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
      10000
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
  try {
    if (renderPass) renderPass.scene = activeScene

    if (_macroRedshiftPending !== null && _macroRedshiftShader?.uniforms?.u_redshift_scale) {
      _macroRedshiftShader.uniforms.u_redshift_scale.value = _macroRedshiftPending
      _macroRedshiftPending = null
    }

    // Keep the inpaint plane in front of the camera (screen-aligned quad).
    if (_inpaintActive && _inpaintMesh && camera) {
      const fwd = new THREE.Vector3(0, 0, -1)
      try {
        fwd.applyQuaternion(camera.quaternion)
      } catch (_) {
        // ignore
      }
      try {
        _inpaintMesh.position.copy(camera.position).add(fwd.multiplyScalar(12))
        _inpaintMesh.quaternion.copy(camera.quaternion)
      } catch (_) {
        // ignore
      }
    }

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
    if (prev === 'macro' && next === 'micro') {
      executeQuantumDive({
        camera,
        gsap,
        onSwitchScene: () => {
          activeScene = microScene
        },
      })
      return
    }

    activeScene = next === 'micro' ? microScene : macroScene
  }
)

watch(
  () => astroStore.currentAgentAction.value?.actionId,
  (id) => {
    if (!id) return
    const action = astroStore.currentAgentAction.value
    const type = String(action?.type || '').trim()

    // Stage 2: run only in macro scene.
    const scale = String(store.currentScale.value || '').trim().toLowerCase()
    if (scale !== 'macro') return

    if (type === ASTRO_AGENT_ACTION_TYPES.EXECUTE_REDSHIFT_PREDICTION) {
      void _executeRedshiftBurst(action?.payload || null)
      return
    }

    if (type === ASTRO_AGENT_ACTION_TYPES.START_MODAL_INPAINT) {
      _startModalInpaint(action?.payload || null)
      return
    }

    if (type === ASTRO_AGENT_ACTION_TYPES.STOP_MODAL_INPAINT) {
      _stopModalInpaint()
    }
  }
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

  disposeThreeEngine({
    renderer,
    controls,
    scenes: [macroScene, microScene],
    disposables: [composer, bloomPass, _inpaintMesh?.material, _inpaintMesh?.geometry],
    animationId,
    cancelAnimationFrameFn: cancelAnimationFrame,
  })

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
  _macroRedshiftPending = null
  _macroRedshiftScale = 0

  _inpaintMesh = null
  _inpaintUniforms = null
  _inpaintActive = false
  _inpaintClickHandler = null
  _inpaintRadiusTween = null
})
</script>

<style scoped>
.three-twin {
  position: relative;
}
</style>
