const DEFAULTS = Object.freeze({
  peakFov: 150,
  settleFov: 60,
  inhaleDuration: 1.2,
  exhaleDuration: 1.5,
  settleZ: 40,
  microPose: { x: 0, y: 0, z: 5 },
})

export function executeQuantumDive({
  camera,
  onSwitchScene,
  gsap,
  peakFov = DEFAULTS.peakFov,
  settleFov = DEFAULTS.settleFov,
  inhaleDuration = DEFAULTS.inhaleDuration,
  exhaleDuration = DEFAULTS.exhaleDuration,
  settleZ = DEFAULTS.settleZ,
  microPose = DEFAULTS.microPose,
} = {}) {
  if (!camera) return
  const g = gsap
  if (!g || typeof g.to !== 'function') {
    // Fallback: hard switch with no animation.
    try {
      onSwitchScene?.()
      camera.position?.set?.(microPose.x, microPose.y, microPose.z)
      camera.fov = settleFov
      camera.updateProjectionMatrix?.()
    } catch (_) {
      // ignore
    }
    return
  }

  g.to(camera, {
    fov: peakFov,
    duration: inhaleDuration,
    ease: 'power2.in',
    onUpdate: () => {
      try {
        camera.updateProjectionMatrix?.()
      } catch (_) {
        // ignore
      }
    },
    onComplete: () => {
      try {
        onSwitchScene?.()
      } catch (_) {
        // ignore
      }

      try {
        camera.position?.set?.(microPose.x, microPose.y, microPose.z)
      } catch (_) {
        // ignore
      }

      g.to(camera, {
        fov: settleFov,
        duration: exhaleDuration,
        ease: 'power2.out',
        onUpdate: () => {
          try {
            camera.updateProjectionMatrix?.()
          } catch (_) {
            // ignore
          }
        },
      })

      try {
        if (camera?.position) {
          g.to(camera.position, {
            z: settleZ,
            duration: exhaleDuration,
            ease: 'power2.out',
          })
        }
      } catch (_) {
        // ignore
      }
    },
  })
}
