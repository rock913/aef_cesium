function _prefersReducedMotion() {
  try {
    return !!window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  } catch (_) {
    return false
  }
}

function _ensureStyle() {
  const id = 'z2x-nav-fade-style'
  if (document.getElementById(id)) return

  const el = document.createElement('style')
  el.id = id
  el.textContent = `
    .z2x-nav-fade {
      position: fixed;
      inset: 0;
      z-index: 99999;
      background: radial-gradient(800px 520px at 50% 40%, rgba(10,15,25,0.55), rgba(0,0,0,0.98));
      opacity: 0;
      pointer-events: none;
      transition: opacity 260ms cubic-bezier(0.16, 1, 0.3, 1);
    }
    .z2x-nav-fade.on {
      opacity: 1;
      pointer-events: auto;
    }
  `
  document.head.appendChild(el)
}

/**
 * Navigate with a short black-fade transition.
 * Works without Vue Router (full navigation), but keeps the experience cinematic.
 */
export function navigateWithFade(href, opts = {}) {
  const url = String(href || '').trim()
  if (!url) return

  const {
    delayMs = 220,
    replace = false,
    reason = '',
  } = opts

  try {
    if (typeof window === 'undefined') return

    // Reduced motion: skip visual transitions.
    if (_prefersReducedMotion()) {
      if (replace) window.location.replace(url)
      else window.location.assign(url)
      return
    }

    _ensureStyle()

    let overlay = document.querySelector('.z2x-nav-fade')
    if (!overlay) {
      overlay = document.createElement('div')
      overlay.className = 'z2x-nav-fade'
      overlay.setAttribute('aria-hidden', 'true')
      if (reason) overlay.setAttribute('data-reason', reason)
      document.body.appendChild(overlay)
    }

    // Allow user to cancel (esc) during the short fade.
    let cancelled = false
    const onKey = (e) => {
      const k = String(e?.key || '').toLowerCase()
      if (k === 'escape') {
        cancelled = true
        try {
          overlay.classList.remove('on')
        } catch (_) {
          // ignore
        }
        window.removeEventListener('keydown', onKey)
      }
    }
    window.addEventListener('keydown', onKey)

    // Trigger fade.
    requestAnimationFrame(() => {
      try {
        overlay.classList.add('on')
      } catch (_) {
        // ignore
      }
    })

    setTimeout(() => {
      try {
        window.removeEventListener('keydown', onKey)
      } catch (_) {
        // ignore
      }
      if (cancelled) return

      if (replace) window.location.replace(url)
      else window.location.assign(url)
    }, Math.max(0, Number(delayMs) || 0))
  } catch (_) {
    // If anything fails, still navigate.
    try {
      if (replace) window.location.replace(url)
      else window.location.assign(url)
    } catch (_) {
      // ignore
    }
  }
}
