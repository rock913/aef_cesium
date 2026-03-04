const _defaultClasses = Object.freeze({
  EffectComposer: null,
  RenderPass: null,
  UnrealBloomPass: null,
  Vector2: null,
})

export function createBloomPipeline({
  renderer,
  scene,
  camera,
  size,
  strength = 1.2,
  threshold = 0.75,
  radius = 0.1,
  classes,
} = {}) {
  const c = { ..._defaultClasses, ...(classes || {}) }
  const EffectComposer = c.EffectComposer
  const RenderPass = c.RenderPass
  const UnrealBloomPass = c.UnrealBloomPass
  const Vector2 = c.Vector2

  if (!EffectComposer || !RenderPass || !UnrealBloomPass || !Vector2) {
    throw new Error('Missing postprocessing classes')
  }
  if (!renderer || !scene || !camera) {
    throw new Error('Missing renderer/scene/camera')
  }

  const width = Number(size?.width || 0) || 1
  const height = Number(size?.height || 0) || 1

  const composer = new EffectComposer(renderer)
  const renderPass = new RenderPass(scene, camera)
  const bloomPass = new UnrealBloomPass(new Vector2(width, height), strength, radius, threshold)

  bloomPass.strength = strength
  bloomPass.threshold = threshold
  bloomPass.radius = radius

  composer.addPass(renderPass)
  composer.addPass(bloomPass)
  composer.setSize(width, height)

  return { composer, renderPass, bloomPass }
}

export function updateBloomParams(bloomPass, params = {}) {
  if (!bloomPass) return
  if (typeof params.strength === 'number') bloomPass.strength = params.strength
  if (typeof params.threshold === 'number') bloomPass.threshold = params.threshold
  if (typeof params.radius === 'number') bloomPass.radius = params.radius
}
