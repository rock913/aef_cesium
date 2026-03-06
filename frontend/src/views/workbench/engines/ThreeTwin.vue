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
let microMesh = null
let microMaterial = null

let terminatorGroup = null
let terminatorEarthMaterial = null
let terminatorShieldMaterial = null

let _macroSpinTween = null

function _buildMacroScene(scene) {
  // Minimal procedural galaxy using InstancedMesh (size tuned for dev; can scale up later).
  const count = 100000
  const geometry = new THREE.SphereGeometry(0.02, 4, 4)
  const material = new THREE.MeshBasicMaterial({ color: 0xffffff })
  const mesh = markRaw(new THREE.InstancedMesh(geometry, material, count))

  const tmp = new THREE.Object3D()
  for (let i = 0; i < count; i += 1) {
    const t = i / count
    const angle = t * Math.PI * 12
    const radius = 2 + t * 18
    tmp.position.set(Math.cos(angle) * radius, (t - 0.5) * 1.2, Math.sin(angle) * radius)
    tmp.updateMatrix()
    mesh.setMatrixAt(i, tmp.matrix)
  }

  scene.add(mesh)
  macroMesh = mesh

  // Demo 15: Terminator Shield (Earth + magnetosphere glow), toggled via layer id 'terminator-shield'.
  try {
    const group = markRaw(new THREE.Group())
    group.visible = false

    const earthGeo = new THREE.SphereGeometry(4.0, 64, 48)
    const earthMat = markRaw(
      new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uLightDir: { value: new THREE.Vector3(0.55, 0.78, 0.28).normalize() },
          uIntensity: { value: 1.0 },
        },
        vertexShader: `
          varying vec3 vN;
          varying vec3 vW;
          void main(){
            vN = normalize(normalMatrix * normal);
            vec4 w = modelMatrix * vec4(position, 1.0);
            vW = w.xyz;
            gl_Position = projectionMatrix * viewMatrix * w;
          }
        `,
        fragmentShader: `
          precision highp float;
          varying vec3 vN;
          uniform float uTime;
          uniform vec3 uLightDir;
          uniform float uIntensity;

          float hash(vec2 p){
            return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
          }

          void main(){
            float ndl = dot(normalize(vN), normalize(uLightDir));
            float day = smoothstep(-0.12, 0.18, ndl);

            vec3 dayColor = vec3(0.08, 0.55, 0.98);
            vec3 nightColor = vec3(0.01, 0.01, 0.05);
            vec3 c = mix(nightColor, dayColor, day);

            // Subtle cloud/noise modulation
            float n = hash(vN.xz * 32.0 + uTime * 0.03);
            c += (n - 0.5) * 0.06 * day;

            // Aurora-ish glow near poles (purely aesthetic)
            float pole = pow(abs(vN.y), 6.0);
            float wave = sin((vN.x + vN.z) * 10.0 + uTime * 0.9) * 0.5 + 0.5;
            vec3 aurora = vec3(0.1, 1.0, 0.75) * pole * wave * 0.22;
            c += aurora * (0.35 + 0.65 * (1.0 - day));

            // Night-side city speckles
            float city = step(0.985, hash(vN.xz * 120.0 + 9.1));
            c += vec3(1.0, 0.75, 0.35) * city * (1.0 - day) * 0.35;

            // Terminator rim glow
            float rim = 1.0 - abs(ndl);
            float terminator = smoothstep(0.55, 0.95, rim);
            c += vec3(0.0, 0.95, 1.0) * terminator * 0.10 * uIntensity;

            gl_FragColor = vec4(c, 1.0);
          }
        `,
      })
    )
    terminatorEarthMaterial = earthMat
    group.add(markRaw(new THREE.Mesh(earthGeo, earthMat)))

    // Atmosphere shell
    const atmoGeo = new THREE.SphereGeometry(4.15, 64, 48)
    const atmoMat = markRaw(
      new THREE.ShaderMaterial({
        uniforms: {
          uIntensity: { value: 1.0 },
        },
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexShader: `
          varying vec3 vN;
          varying vec3 vV;
          void main(){
            vN = normalize(normalMatrix * normal);
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            vV = normalize(-mv.xyz);
            gl_Position = projectionMatrix * mv;
          }
        `,
        fragmentShader: `
          precision highp float;
          varying vec3 vN;
          varying vec3 vV;
          uniform float uIntensity;
          void main(){
            float fres = pow(1.0 - max(0.0, dot(vN, vV)), 3.0);
            vec3 c = vec3(0.08, 0.65, 1.0) * fres * 0.7 * uIntensity;
            gl_FragColor = vec4(c, fres * 0.55);
          }
        `,
      })
    )
    group.add(markRaw(new THREE.Mesh(atmoGeo, atmoMat)))

    // Shield dome
    const shieldGeo = new THREE.SphereGeometry(5.25, 64, 48)
    const shieldMat = markRaw(
      new THREE.ShaderMaterial({
        uniforms: {
          uIntensity: { value: 1.0 },
        },
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexShader: `
          varying vec3 vN;
          varying vec3 vV;
          void main(){
            vN = normalize(normalMatrix * normal);
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            vV = normalize(-mv.xyz);
            gl_Position = projectionMatrix * mv;
          }
        `,
        fragmentShader: `
          precision highp float;
          varying vec3 vN;
          varying vec3 vV;
          uniform float uIntensity;
          void main(){
            float fres = pow(1.0 - max(0.0, dot(vN, vV)), 2.2);
            float bands = 0.5 + 0.5 * sin((vN.y * 10.0) + (vN.x * 6.0));
            vec3 c = mix(vec3(0.5, 0.0, 1.0), vec3(0.0, 0.95, 1.0), bands);
            gl_FragColor = vec4(c * fres * 0.65 * uIntensity, fres * 0.35 * uIntensity);
          }
        `,
      })
    )
    terminatorShieldMaterial = shieldMat
    group.add(markRaw(new THREE.Mesh(shieldGeo, shieldMat)))

    // Magnetosphere field lines (simple parametric loops)
    const lineMat = markRaw(
      new THREE.LineBasicMaterial({
        color: 0x00f0ff,
        transparent: true,
        opacity: 0.28,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    )

    function buildLoop(rA, rB, segments = 256) {
      const pts = []
      for (let i = 0; i <= segments; i += 1) {
        const t = (i / segments) * Math.PI * 2
        pts.push(new THREE.Vector3(Math.cos(t) * rA, Math.sin(t) * rB, 0))
      }
      const g = new THREE.BufferGeometry().setFromPoints(pts)
      return markRaw(new THREE.Line(g, lineMat))
    }

    const loops = [
      { rA: 6.2, rB: 4.8, rx: 0.0, ry: 0.0, rz: 0.0 },
      { rA: 6.8, rB: 5.2, rx: 0.0, ry: Math.PI / 2, rz: 0.0 },
      { rA: 7.4, rB: 5.6, rx: Math.PI / 2, ry: 0.0, rz: 0.0 },
      { rA: 8.8, rB: 6.2, rx: 0.35, ry: 0.0, rz: 0.0 },
      { rA: 9.4, rB: 6.6, rx: 0.0, ry: 0.35, rz: 0.0 },
    ]
    for (const l of loops) {
      const line = buildLoop(l.rA, l.rB)
      line.rotation.set(l.rx, l.ry, l.rz)
      group.add(line)
    }

    scene.add(group)
    terminatorGroup = group
  } catch (_) {
    terminatorGroup = null
    terminatorEarthMaterial = null
    terminatorShieldMaterial = null
  }
}

function _buildMicroScene(scene) {
  const count = 8000
  const geometry = new THREE.IcosahedronGeometry(0.08, 0)
  const material = new THREE.MeshPhysicalMaterial({
    color: 0x7dd3fc,
    transparent: true,
    opacity: 0.85,
    roughness: 0.12,
    metalness: 0.0,
    transmission: 0.85,
    ior: 1.4,
    thickness: 0.5,
  })
  const mesh = markRaw(new THREE.InstancedMesh(geometry, material, count))
  microMaterial = material

  const tmp = new THREE.Object3D()
  const grid = Math.ceil(Math.cbrt(count))
  let idx = 0
  for (let x = 0; x < grid && idx < count; x += 1) {
    for (let y = 0; y < grid && idx < count; y += 1) {
      for (let z = 0; z < grid && idx < count; z += 1) {
        tmp.position.set((x - grid / 2) * 0.25, (y - grid / 2) * 0.25, (z - grid / 2) * 0.25)
        tmp.updateMatrix()
        mesh.setMatrixAt(idx, tmp.matrix)
        idx += 1
      }
    }
  }

  scene.add(mesh)
  microMesh = mesh
}

function _applyThreeLayerMapping(layers) {
  const mapped = mapLayersToThreeParams(layers)

  // Optional intensity parameter for the shield (kept outside mapping for simplicity).
  try {
    const l = (Array.isArray(layers) ? layers : []).find((x) => String(x?.id || '') === 'terminator-shield')
    const intensityRaw = Number(l?.params?.intensity)
    const intensity = Number.isFinite(intensityRaw) ? Math.max(0, Math.min(3, intensityRaw)) : 1.0
    if (terminatorEarthMaterial?.uniforms?.uIntensity) terminatorEarthMaterial.uniforms.uIntensity.value = intensity
    if (terminatorShieldMaterial?.uniforms?.uIntensity) terminatorShieldMaterial.uniforms.uIntensity.value = intensity
  } catch (_) {
    // ignore
  }

  if (macroMesh) {
    try {
      macroMesh.visible = !!mapped.macroSpiralVisible
    } catch (_) {
      // ignore
    }
  }

  if (terminatorGroup) {
    try {
      terminatorGroup.visible = !!mapped.terminatorShieldVisible
    } catch (_) {
      // ignore
    }
  }

  if (microMesh) {
    try {
      microMesh.visible = !!mapped.microAtomsVisible
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

async function rebuildMicroLattice() {
  if (!microMesh) return
  // Quick "bond break/reform" vibe: jitter positions then settle.
  const count = microMesh.count || 0
  if (!count) return

  const tmp = new THREE.Object3D()
  const base = []
  for (let i = 0; i < Math.min(count, 600); i += 1) {
    const m = new THREE.Matrix4()
    microMesh.getMatrixAt(i, m)
    base.push(m)
  }

  function jitter(scale) {
    for (let i = 0; i < base.length; i += 1) {
      tmp.matrix.copy(base[i])
      tmp.position.setFromMatrixPosition(tmp.matrix)
      tmp.position.x += (Math.random() - 0.5) * scale
      tmp.position.y += (Math.random() - 0.5) * scale
      tmp.position.z += (Math.random() - 0.5) * scale
      tmp.updateMatrix()
      microMesh.setMatrixAt(i, tmp.matrix)
    }
    microMesh.instanceMatrix.needsUpdate = true
  }

  jitter(0.8)
  await new Promise((r) => setTimeout(r, 220))
  jitter(0.25)
  await new Promise((r) => setTimeout(r, 180))
  // restore
  for (let i = 0; i < base.length; i += 1) {
    microMesh.setMatrixAt(i, base[i])
  }
  microMesh.instanceMatrix.needsUpdate = true
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

  // Lightweight shader time update for the terminator demo (no-op when disabled).
  try {
    if (terminatorGroup?.visible && terminatorEarthMaterial?.uniforms?.uTime) {
      terminatorEarthMaterial.uniforms.uTime.value = (performance.now() || 0) / 1000.0
      terminatorGroup.rotation.y += 0.00035
    }
  } catch (_) {
    // ignore
  }
  try {
    controls?.update?.()
  } catch (_) {
    // ignore
  }
  try {
    if (renderPass) renderPass.scene = activeScene
    if (composer) composer.render()
    else renderer?.render?.(activeScene, camera)
  } catch (_) {
    // ignore
  }
}

onMounted(() => {
  initEngine()
  _applyThreeLayerMapping(props.layers)
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

defineExpose({
  highlightMacroCluster,
  spinMacroCamera,
  rebuildMicroLattice,
})

onBeforeUnmount(() => {
  try {
    window.removeEventListener('resize', onResize)
  } catch (_) {
    // ignore
  }

  disposeThreeEngine({
    renderer,
    controls,
    scenes: [macroScene, microScene],
    disposables: [composer, bloomPass],
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
  microMesh = null
  microMaterial = null
})
</script>

<style scoped>
.three-twin {
  position: relative;
}
</style>
