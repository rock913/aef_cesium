function _disposeMaterial(material) {
  if (!material) return
  if (Array.isArray(material)) {
    for (const m of material) {
      try {
        m?.dispose?.()
      } catch (_) {
        // ignore
      }
    }
    return
  }
  try {
    material?.dispose?.()
  } catch (_) {
    // ignore
  }
}

export function disposeThreeEngine({
  renderer,
  controls,
  scenes,
  disposables,
  animationId,
  cancelAnimationFrameFn,
} = {}) {
  const cancelFn = typeof cancelAnimationFrameFn === 'function' ? cancelAnimationFrameFn : null
  if (cancelFn && typeof animationId === 'number') {
    try {
      cancelFn(animationId)
    } catch (_) {
      // ignore
    }
  }

  try {
    controls?.dispose?.()
  } catch (_) {
    // ignore
  }

  const list = Array.isArray(scenes) ? scenes : []
  for (const scene of list) {
    try {
      scene?.traverse?.((obj) => {
        try {
          obj?.geometry?.dispose?.()
        } catch (_) {
          // ignore
        }
        _disposeMaterial(obj?.material)
      })
    } catch (_) {
      // ignore
    }
  }

  const extra = Array.isArray(disposables) ? disposables : []
  for (const d of extra) {
    try {
      d?.dispose?.()
    } catch (_) {
      // ignore
    }
  }

  if (renderer) {
    try {
      renderer?.dispose?.()
    } catch (_) {
      // ignore
    }
    try {
      renderer?.forceContextLoss?.()
    } catch (_) {
      // ignore
    }
    try {
      renderer?.domElement?.remove?.()
    } catch (_) {
      // ignore
    }
  }
}
