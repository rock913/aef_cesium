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
import { createBloomPipeline } from './threePostprocessing.js'

const emit = defineEmits(['ready'])

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
    if (composer) composer.render()
    else renderer?.render?.(activeScene, camera)
  } catch (_) {
    // ignore
  }
}

onMounted(() => {
  initEngine()
  animate()
  emit('ready')
})

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
})
</script>

<style scoped>
.three-twin {
  position: relative;
}
</style>
