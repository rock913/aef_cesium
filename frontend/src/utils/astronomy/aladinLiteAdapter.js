let _loadPromise = null

const DEFAULT_ALADIN_V3_URL = 'https://aladin.u-strasbg.fr/AladinLite/api/v3/latest/aladin.js'
const DEFAULT_ALADIN_V3_CSS = 'https://aladin.u-strasbg.fr/AladinLite/api/v3/latest/aladin.css'

function _canUseDom() {
  return typeof window !== 'undefined' && typeof document !== 'undefined'
}

function _ensureCss(href) {
  if (!_canUseDom()) return
  const url = String(href || '').trim()
  if (!url) return
  try {
    const existing = document.querySelector(`link[data-aladin-lite="1"][href="${url}"]`)
    if (existing) return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = url
    link.setAttribute('data-aladin-lite', '1')
    document.head.appendChild(link)
  } catch (_) {
    // ignore
  }
}

export async function loadAladinLiteV3({ scriptUrl = DEFAULT_ALADIN_V3_URL, cssUrl = DEFAULT_ALADIN_V3_CSS } = {}) {
  if (!_canUseDom()) return null

  try {
    // Aladin Lite attaches a global `A`.
    if (window.A && typeof window.A === 'object') return window.A
  } catch (_) {
    // ignore
  }

  if (_loadPromise) return _loadPromise

  _ensureCss(cssUrl)

  _loadPromise = new Promise((resolve) => {
    try {
      const url = String(scriptUrl || '').trim()
      if (!url) return resolve(null)

      const existing = document.querySelector(`script[data-aladin-lite="1"][src="${url}"]`)
      if (existing) {
        existing.addEventListener('load', () => resolve(window.A || null), { once: true })
        existing.addEventListener('error', () => resolve(null), { once: true })
        return
      }

      const s = document.createElement('script')
      s.src = url
      s.async = true
      s.defer = true
      s.setAttribute('data-aladin-lite', '1')
      s.onload = () => resolve(window.A || null)
      s.onerror = () => resolve(null)
      document.head.appendChild(s)
    } catch (_) {
      resolve(null)
    }
  })

  return _loadPromise
}

function _call(aladin, names, ...args) {
  if (!aladin) return false
  const methods = Array.isArray(names) ? names : [names]
  for (const n of methods) {
    const fn = aladin?.[n]
    if (typeof fn === 'function') {
      try {
        fn.apply(aladin, args)
        return true
      } catch (_) {
        // ignore
      }
    }
  }
  return false
}

export async function initAladinLiteV3({
  container,
  raDeg = 0,
  decDeg = 0,
  fovDeg = 60,
  survey = 'P/DSS2/color',
} = {}) {
  if (!_canUseDom()) return null
  if (!container) return null

  const A = await loadAladinLiteV3()
  if (!A) return null

  const target = `${Number(raDeg) || 0} ${Number(decDeg) || 0}`
  const fov = Number.isFinite(Number(fovDeg)) ? Number(fovDeg) : 60

  try {
    if (typeof A.aladin === 'function') {
      const aladin = A.aladin(container, {
        target,
        fov,
        survey,
        showReticle: false,
        showFrame: false,
        showCooGrid: false,
        showSimbadPointerControl: false,
        fullScreen: false,
      })
      return aladin || null
    }
  } catch (_) {
    // ignore
  }

  return null
}

export function setAladinView(aladin, { raDeg, decDeg, fovDeg } = {}) {
  if (!aladin) return
  const ra = Number(raDeg)
  const dec = Number(decDeg)
  const fov = Number(fovDeg)

  if (Number.isFinite(ra) && Number.isFinite(dec)) {
    _call(aladin, ['gotoRaDec', 'gotoPosition', 'setCenter'], ra, dec)
    // Some builds use a string target.
    if (!_call(aladin, ['gotoRaDec', 'gotoPosition', 'setCenter'], ra, dec)) {
      try {
        _call(aladin, ['gotoObject'], `${ra} ${dec}`)
      } catch (_) {
        // ignore
      }
    }
  }

  if (Number.isFinite(fov)) {
    _call(aladin, ['setFov', 'setFoV'], fov)
  }
}

export function setAladinSurvey(aladin, survey) {
  if (!aladin) return
  const s = String(survey || '').trim()
  if (!s) return
  _call(aladin, ['setImageSurvey', 'setSurvey', 'setBaseImageLayer'], s)
}

export function destroyAladin(aladin, container) {
  try {
    _call(aladin, ['destroy', 'dispose'])
  } catch (_) {
    // ignore
  }
  if (container && _canUseDom()) {
    try {
      container.innerHTML = ''
    } catch (_) {
      // ignore
    }
  }
}
