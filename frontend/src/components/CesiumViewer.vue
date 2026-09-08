<template>
  <div class="cesium-viewer-container">
    <div id="cesiumContainer" ref="cesiumContainer"></div>

    <!-- Keep required Cesium/imagery credits visible, but in a less intrusive place -->
    <div ref="creditContainer" class="credit-container"></div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">{{ loadingText }}</div>
    </div>
  </div>
</template>

<script>
import * as Cesium from 'cesium'
import {
  applyCinematicLighting,
  addHeritageModel,
  bindAnchorLabels,
  addWindStreamlines,
  clearCh9Scene,
} from '../scenes/ch9_cesium_l5.js'
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

export default {
  name: 'CesiumViewer',
  props: {
    initialLocation: {
      type: Object,
      default: () => ({ lat: 39.0500, lon: 115.9800, height: 15000 })
    }
  },
  emits: ['viewer-ready', 'camera-moved', 'map-center-changed', 'imagery-error', 'tile-load-progress', 'map-click'],
  
  setup(props, { emit }) {
    const cesiumContainer = ref(null)
    const creditContainer = ref(null)
    const loading = ref(true)
    const loadingText = ref('初始化地球引擎...')

    let disposed = false
    
    let viewer = null
    let currentAILayer = null
    let currentAIProviderUnsub = null
    let currentBasemapLayer = null
    let currentBasemapProviderUnsub = null
    let photorealisticTileset = null
    let photorealisticTilesetBaseStyle = null
    let photorealisticTilesetDimStyle = null
    let isAILayerActive = false
    let lastAppliedTilesetShow = null
    let lastAppliedTilesetStyle = null
    let hiddenBaseLayers = []
    let tileLoadUnsub = null
    let ionBaseProviderUnsub = null
    let terrainErrorUnsub = null
    let rotationTick = null
    let fadeTimer = null
    let centerTick = null
    let centerRafPending = false
    let lastCenterLat = null
    let lastCenterLon = null
    let clickHandler = null
    let inspectionBeaconEntity = null
    let insarPointEntities = []
    let heritageBuildingEntities = []
    let heritagePointDataSource = null
    let heritagePulseTimer = null
    let windTrailEntities = []
    let feaAnchorEntities = []
    let feaPulseTimer = null
    let cinematicBloomStage = null
    
    onMounted(() => {
      Promise.resolve()
        .then(() => initViewer())
        .catch((error) => {
          console.error('Cesium初始化失败:', error)
          loading.value = false
          loadingText.value = '初始化失败: ' + (error?.message || String(error))
        })
    })
    
    onBeforeUnmount(() => {
      disposed = true
      clearInspectionBeacon()
      clearInsarPoints()
      if (viewer) {
        if (clickHandler) {
          try {
            clickHandler.destroy()
          } catch (_) {
            // ignore
          }
          clickHandler = null
        }
        if (tileLoadUnsub) tileLoadUnsub()
        if (currentAIProviderUnsub) currentAIProviderUnsub()
        if (currentBasemapProviderUnsub) currentBasemapProviderUnsub()
        if (ionBaseProviderUnsub) ionBaseProviderUnsub()
        if (terrainErrorUnsub) terrainErrorUnsub()
        if (rotationTick) {
          try {
            viewer.clock.onTick.removeEventListener(rotationTick)
          } catch (_) {
            // ignore
          }
          rotationTick = null
        }
        if (fadeTimer) {
          clearInterval(fadeTimer)
          fadeTimer = null
        }
        if (centerTick) {
          try {
            viewer.camera.changed.removeEventListener(centerTick)
          } catch (_) {
            // ignore
          }
          centerTick = null
        }
        try {
          const destroyed = typeof viewer.isDestroyed === 'function' ? viewer.isDestroyed() : false
          if (!destroyed) viewer.destroy()
        } catch (_) {
          // ignore
        } finally {
          viewer = null
        }
      }
    })

    function _updatePhotorealisticTilesetVisibility() {
      if (!viewer || !photorealisticTileset) return

      // Workbench note:
      // In the Workbench, AI imagery layers are mounted by `EngineRouter` directly
      // onto `viewer.imageryLayers`, not via this component's `loadAILayer()`.
      // Detect such externally-managed overlays so the photorealistic tileset
      // doesn't occlude the imagery stack at close zoom.
      const _hasExternalOverlay = () => {
        try {
          const layers = viewer?.imageryLayers
          if (!layers) return false
          const n = typeof layers.length === 'number' ? layers.length : 0
          for (let i = 0; i < n; i++) {
            const layer = layers.get(i)
            if (!layer) continue
            if (layer === currentBasemapLayer) continue
            if (layer === currentAILayer) continue
            // Only treat marked overlays as AI overlays.
            if (!layer.__oneearthOverlay) continue
            const show = layer.show !== false
            const alpha = (layer.alpha === undefined || layer.alpha === null) ? 1.0 : Number(layer.alpha)
            if (show && (!Number.isFinite(alpha) || alpha > 0.02)) {
              return true
            }
          }
        } catch (_) {
          // ignore
        }
        return false
      }

      const occlusionMode = String(import.meta.env.VITE_PHOTOREALISTIC_AI_OCCLUSION || 'hide')
        .trim()
        .toLowerCase()

      const rawThreshold = String(import.meta.env.VITE_PHOTOREALISTIC_VISIBILITY_THRESHOLD_M || '').trim()
      const thresholdM = Number(rawThreshold)
      const visibilityThresholdM = Number.isFinite(thresholdM) && thresholdM > 0 ? thresholdM : 2000000

      const cameraHeight = Number(viewer.camera?.positionCartographic?.height)
      const isFarView = Number.isFinite(cameraHeight) ? (cameraHeight >= visibilityThresholdM) : false

      let desiredShow = true
      let desiredStyle = photorealisticTilesetBaseStyle

      const aiOverlayActive = !!(isAILayerActive || _hasExternalOverlay())

      // Rule 1 (highest priority): AI overlay active -> occlude tileset.
      if (aiOverlayActive && occlusionMode !== 'none' && occlusionMode !== 'off') {
        if (occlusionMode === 'dim') {
          if (!photorealisticTilesetDimStyle) {
            photorealisticTilesetDimStyle = new Cesium.Cesium3DTileStyle({
              color: "color('white', 0.25)"
            })
          }
          desiredShow = true
          desiredStyle = photorealisticTilesetDimStyle
        } else {
          desiredShow = false
          desiredStyle = photorealisticTilesetBaseStyle
        }
      } else {
        // Rule 2: Far (homepage / space view) -> hide tileset to avoid coarse root-tile patchwork.
        desiredShow = !isFarView
        desiredStyle = photorealisticTilesetBaseStyle
      }

      if (lastAppliedTilesetShow === desiredShow && lastAppliedTilesetStyle === desiredStyle) return

      try {
        photorealisticTileset.show = desiredShow
        photorealisticTileset.style = desiredStyle
        lastAppliedTilesetShow = desiredShow
        lastAppliedTilesetStyle = desiredStyle
      } catch (_) {
        // ignore
      }
    }
    
    async function initViewer() {
      if (disposed) return
      const rawIonToken = String(import.meta.env.VITE_CESIUM_TOKEN || '').trim()
      const ionToken = rawIonToken
        .replace(/^"(.*)"$/, '$1')
        .replace(/^'(.*)'$/, '$1')
        .trim()
      const hasIonToken = !!ionToken
      const disableDefaultImagery = String(import.meta.env.VITE_DISABLE_DEFAULT_IMAGERY || '').trim() === '1'
      const basemapMode = String(import.meta.env.VITE_BASEMAP || '').trim().toLowerCase()
      if (hasIonToken) {
        Cesium.Ion.defaultAccessToken = ionToken

        // Some client networks cannot reach Cesium Ion / Google endpoints directly.
        // When enabled, proxy all Ion API + assets through our own backend (/api/*).
        try {
          const ionProxyFlag = String(import.meta.env.VITE_ION_PROXY || '').trim()
          const useIonProxy = (ionProxyFlag === '1') || (import.meta.env.PROD && ionProxyFlag !== '0')
          if (useIonProxy && Cesium?.Ion && Cesium?.Resource) {
            Cesium.Ion.defaultServer = new Cesium.Resource({
              url: '/api/ion/'
            })
          }
        } catch (_) {
          // ignore
        }
      }

      if (!cesiumContainer.value) {
        // Can happen if the component unmounts quickly (e.g., scale switch) while
        // initViewer is scheduled in a microtask, or if DOM is not yet flushed.
        if (disposed) return
        try {
          await nextTick()
        } catch (_) {
          // ignore
        }
        if (disposed) return
        if (!cesiumContainer.value) throw new Error('Cesium container element not found')
      }

      async function _createOfficialGoogle2DSatelliteProvider() {
        const googleKey = String(import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '').trim()
        const sessionUrl = googleKey
          ? `/api/google-tiles/v1/createSession?key=${encodeURIComponent(googleKey)}`
          : '/api/google-tiles/v1/createSession'

        const resp = await fetch(sessionUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            mapType: 'satellite',
            language: 'zh-CN',
            region: 'CN'
          })
        })

        if (!resp.ok) {
          throw new Error(`Google createSession failed: ${resp.status}`)
        }

        const data = await resp.json()
        const session = String(data?.session || data?.sessionToken || '').trim()
        if (!session) {
          throw new Error('Google createSession did not return session')
        }

        // Prefer NOT embedding key in the tile URL for production.
        // If backend has GOOGLE_MAPS_API_KEY set, it will inject ?key automatically.
        const tileUrl = googleKey
          ? `/api/google-tiles/v1/2dtiles/{z}/{x}/{y}?session=${encodeURIComponent(session)}&key=${encodeURIComponent(googleKey)}`
          : `/api/google-tiles/v1/2dtiles/{z}/{x}/{y}?session=${encodeURIComponent(session)}`

        return new Cesium.UrlTemplateImageryProvider({
          url: tileUrl,
          tilingScheme: new Cesium.WebMercatorTilingScheme(),
          maximumLevel: 20,
          enablePickFeatures: false
        })
      }

      function _createUnofficialGoogleXyzSatelliteProvider() {
        // NOTE: This is intentionally a "test-only" option.
        // It uses an undocumented URL pattern and may be subject to change or terms.
        const enabled = String(import.meta.env.VITE_GOOGLE_XYZ_ENABLE || '').trim() === '1'
        if (!enabled) {
          throw new Error('Google XYZ basemap is disabled (set VITE_GOOGLE_XYZ_ENABLE=1)')
        }

        const lyrs = String(import.meta.env.VITE_GOOGLE_XYZ_LYRS || 's').trim() || 's'

        // Prefer subdomain rotation by default for resilience (mt0..mt3).
        // Allow pinning a single host via VITE_GOOGLE_XYZ_SERVER=mt1|mt2|mt3.
        const server = String(import.meta.env.VITE_GOOGLE_XYZ_SERVER || '').trim()
        const useSubdomains = !server || server === 'auto'
        const url = useSubdomains
          ? `https://mt{s}.google.com/vt/lyrs=${encodeURIComponent(lyrs)}&x={x}&y={y}&z={z}`
          : `https://${server}.google.com/vt/lyrs=${encodeURIComponent(lyrs)}&x={x}&y={y}&z={z}`

        return new Cesium.UrlTemplateImageryProvider({
          url,
          ...(useSubdomains ? { subdomains: ['0', '1', '2', '3'] } : {}),
          tilingScheme: new Cesium.WebMercatorTilingScheme(),
          maximumLevel: 20,
          enablePickFeatures: false
        })
      }

      // IMPORTANT: `Viewer` expects a TerrainProvider on `terrainProvider`.
      // Passing a TerrainProvider into `terrain` can crash with:
      //   Cannot read properties of undefined (reading 'addEventListener')
      // because providers like EllipsoidTerrainProvider don't have `readyEvent`.
      let terrainProvider = new Cesium.EllipsoidTerrainProvider()
      const disableWorldTerrainEnv = String(import.meta.env.VITE_DISABLE_WORLD_TERRAIN || '').trim() === '1'
      let disableWorldTerrainQuery = false
      // Small helper: avoid hanging forever on network-dependent promises.
      async function _withTimeout(promise, ms, label) {
        const timeoutMs = Number.isFinite(Number(ms)) ? Number(ms) : 12000
        const tag = String(label || 'timeout')
        let t = null
        const timeoutPromise = new Promise((_, reject) => {
          t = setTimeout(() => reject(new Error(`${tag}_timeout_${timeoutMs}ms`)), timeoutMs)
        })
        try {
          return await Promise.race([promise, timeoutPromise])
        } finally {
          try {
            if (t) clearTimeout(t)
          } catch (_) {
            // ignore
          }
        }
      }

      try {
        const q = new URLSearchParams(String(window?.location?.search || ''))
        const v = String(q.get('terrain') || '').trim().toLowerCase()
        disableWorldTerrainQuery = v === 'off' || v === '0' || v === 'false'
      } catch (_) {
        disableWorldTerrainQuery = false
      }
      const disableWorldTerrain = disableWorldTerrainEnv || disableWorldTerrainQuery

      if (hasIonToken && !disableWorldTerrain) {
        try {
          if (typeof Cesium.createWorldTerrainAsync === 'function') {
            terrainProvider = await _withTimeout(
              Cesium.createWorldTerrainAsync({
                requestWaterMask: true,
                requestVertexNormals: true
              }),
              8000,
              'world_terrain'
            )
          } else {
            // Fallback: keep ellipsoid if this build doesn't expose the async helper.
            terrainProvider = new Cesium.EllipsoidTerrainProvider()
          }
        } catch (e) {
          const msg = String(e?.message || e || '')
          console.warn(
            '⚠️  World Terrain unavailable; using ellipsoid terrain. ' +
              'Tip: set VITE_DISABLE_WORLD_TERRAIN=1 (or add ?terrain=off) in restricted networks. ' +
              (msg ? `(${msg})` : '')
          )
          terrainProvider = new Cesium.EllipsoidTerrainProvider()
        }
      }

      // (viewer is created further down; once created we will enable globe lighting.)

      try {
        // Basemap strategy:
        // - If Ion token exists, do NOT override imageryProvider/baseLayer so Cesium loads its stable default imagery.
        //   This fixes the "blue grid" and many third-party basemap failures.
        // - If no token, fall back to a grid so the globe is still visible.
        // - If VITE_DISABLE_DEFAULT_IMAGERY=1, avoid Cesium default imagery (Bing). Prefer a same-origin OSM basemap
        //   via backend `/api/basemap/osm/` to prevent client-side network blocks (virtualearth.net, CORS, etc).
        // - You can also force a mode via VITE_BASEMAP=osm|grid|default.
        const fallbackImageryProvider = new Cesium.GridImageryProvider()

        let forcedBaseLayer = null
        let forcedBaseProvider = null
        try {
          const wantOsm = (basemapMode === 'osm') || disableDefaultImagery
          const wantGrid = (basemapMode === 'grid')
          const wantGoogleOfficial = (basemapMode === 'google_official') || (basemapMode === 'google-official')
          const wantGoogleXyz = (basemapMode === 'google_xyz') || (basemapMode === 'google-xyz') || (basemapMode === 'google_unofficial')
          if (wantGoogleOfficial) {
            const provider = await _createOfficialGoogle2DSatelliteProvider()
            forcedBaseProvider = provider
            forcedBaseLayer = new Cesium.ImageryLayer(provider)
          } else if (wantGoogleXyz) {
            const provider = _createUnofficialGoogleXyzSatelliteProvider()
            forcedBaseProvider = provider
            forcedBaseLayer = new Cesium.ImageryLayer(provider)
          } else if (wantOsm) {
            const osmProvider = new Cesium.OpenStreetMapImageryProvider({
              // Backend route is `/api/basemap/osm/{z}/{x}/{y}.png`
              url: '/api/basemap/osm/'
            })
            forcedBaseProvider = osmProvider
            forcedBaseLayer = new Cesium.ImageryLayer(osmProvider)
          } else if (wantGrid) {
            forcedBaseProvider = fallbackImageryProvider
            forcedBaseLayer = new Cesium.ImageryLayer(fallbackImageryProvider)
          }
        } catch (e) {
          if ((basemapMode === 'google_xyz') || (basemapMode === 'google-xyz') || (basemapMode === 'google_unofficial')) {
            console.warn('[OneEarth Cesium] Google XYZ basemap init failed; falling back to OSM.', e)
            try {
              const osmProvider = new Cesium.OpenStreetMapImageryProvider({ url: '/api/basemap/osm/' })
              forcedBaseProvider = osmProvider
              forcedBaseLayer = new Cesium.ImageryLayer(osmProvider)
            } catch (_) {
              forcedBaseProvider = fallbackImageryProvider
              forcedBaseLayer = new Cesium.ImageryLayer(fallbackImageryProvider)
            }
          }
          // If the official Google basemap fails (missing key/session/network), fall back.
          if ((basemapMode === 'google_official') || (basemapMode === 'google-official')) {
            console.warn('[OneEarth Cesium] Google official 2D basemap init failed; falling back to OSM.', e)
            try {
              const osmProvider = new Cesium.OpenStreetMapImageryProvider({ url: '/api/basemap/osm/' })
              forcedBaseProvider = osmProvider
              forcedBaseLayer = new Cesium.ImageryLayer(osmProvider)
            } catch (_) {
              forcedBaseProvider = fallbackImageryProvider
              forcedBaseLayer = new Cesium.ImageryLayer(fallbackImageryProvider)
            }
          }
          // If user explicitly disabled default imagery but OSM provider creation fails,
          // fall back to a local grid rather than re-enabling default Bing.
          if (disableDefaultImagery) {
            forcedBaseProvider = fallbackImageryProvider
            forcedBaseLayer = new Cesium.ImageryLayer(fallbackImageryProvider)
          }
        }

        // IMPORTANT: initViewer awaits async setup (terrain/basemap/session fetch).
        // If the component unmounts during those awaits, the container ref becomes null
        // and Cesium throws "container is required". Abort cleanly.
        if (disposed) return
        const containerEl = cesiumContainer.value
        if (!containerEl) return

        viewer = new Cesium.Viewer(containerEl, {
          creditContainer: creditContainer.value,
          terrainProvider,

          baseLayerPicker: false,
          ...(forcedBaseLayer === false
            ? { baseLayer: false }
            : (forcedBaseLayer
              ? { baseLayer: forcedBaseLayer }
              : (hasIonToken
                ? {}
                : { baseLayer: new Cesium.ImageryLayer(fallbackImageryProvider) }))),
          
          // UI 控制
          animation: false,
          timeline: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,

          // Workbench UX: avoid Cesium's default InfoBox overlaying our LayerTree.
          // (Picking/selecting GeoJSON entities can otherwise spawn an InfoBox in the top-right.)
          infoBox: false,
          selectionIndicator: false,
          
          // 性能优化
          requestRenderMode: false,
          maximumRenderTimeChange: Infinity
        })

        // If we got disposed mid-init, tear down immediately to avoid
        // leaked WebGL contexts / later destroyed-object errors.
        if (disposed) {
          try {
            const destroyed = typeof viewer.isDestroyed === 'function' ? viewer.isDestroyed() : false
            if (!destroyed) viewer.destroy()
          } catch (_) {
            // ignore
          } finally {
            viewer = null
          }
          return
        }

        // Cinematic: enable lighting for a better terminator line + atmosphere feel.
        try {
          if (viewer?.scene?.globe) {
            viewer.scene.globe.enableLighting = true
            // Keep atmosphere visible (default true in Cesium, but be explicit).
            viewer.scene.globe.showGroundAtmosphere = true
          }
          if (viewer?.scene?.skyAtmosphere) {
            viewer.scene.skyAtmosphere.show = true
          }
        } catch (_) {
          // ignore
        }

        // Offline-safe behavior:
        // Even if `createWorldTerrainAsync()` succeeds, restricted networks can still reset
        // the actual tile requests (assets.ion.cesium.com). Cesium then keeps retrying tiles
        // and spams the console. If we detect the first terrain error, downgrade to ellipsoid
        // so the globe can continue rendering without repeated failing requests.
        try {
          const tp = viewer?.terrainProvider
          const shouldWatchTerrainErrors = !!(hasIonToken && !disableWorldTerrain)
          if (shouldWatchTerrainErrors && tp?.errorEvent?.addEventListener) {
            let switched = false
            const onTerrainError = (err) => {
              if (switched) return
              switched = true

              let detail = ''
              try {
                const msg = String(err?.message || err || '').trim()
                if (msg) detail = ` (${msg})`
              } catch (_) {
                // ignore
              }

              console.warn(
                '⚠️  World Terrain tile request failed; switching to ellipsoid terrain.' +
                  ' Tip: add ?terrain=off or set VITE_DISABLE_WORLD_TERRAIN=1 for offline demos.' +
                  detail
              )

              try {
                const ellipsoid = new Cesium.EllipsoidTerrainProvider()
                viewer.terrainProvider = ellipsoid
                if (viewer?.scene?.globe) viewer.scene.globe.terrainProvider = ellipsoid
              } catch (_) {
                // ignore
              }

              try {
                tp.errorEvent.removeEventListener(onTerrainError)
              } catch (_) {
                // ignore
              }
            }

            tp.errorEvent.addEventListener(onTerrainError)
            terrainErrorUnsub = () => {
              try {
                tp.errorEvent.removeEventListener(onTerrainError)
              } catch (_) {
                // ignore
              }
            }
          }
        } catch (_) {
          // ignore
        }

        // Optional: custom high-res skybox assets (drop-in, offline-friendly).
        // Place files under: /public/zero2x/skybox/{px,nx,py,ny,pz,nz}.jpg
        // IMPORTANT: in Vite dev, unknown asset paths may return index.html with 200.
        // Guard by requiring `Content-Type: image/*` for ALL 6 faces.
        try {
          const base = '/zero2x/skybox'
          const faces = ['px', 'nx', 'py', 'ny', 'pz', 'nz']
          const urls = faces.map((k) => `${base}/${k}.jpg`)
          const checks = await Promise.all(
            urls.map(async (u) => {
              try {
                const r = await fetch(u, { method: 'HEAD', cache: 'no-store' })
                if (!r || !r.ok) return false
                const ct = String(r.headers?.get?.('content-type') || '').toLowerCase()
                return ct.startsWith('image/')
              } catch (_) {
                return false
              }
            })
          )

          if (checks.every(Boolean)) {
            viewer.scene.skyBox = new Cesium.SkyBox({
              sources: {
                positiveX: urls[0],
                negativeX: urls[1],
                positiveY: urls[2],
                negativeY: urls[3],
                positiveZ: urls[4],
                negativeZ: urls[5]
              }
            })
          } else {
            // Skip silently; default Cesium skybox remains.
          }
        } catch (_) {
          // ignore
        }

        // Enforce explicit basemap selection.
        // In some Cesium builds, providing an Ion token can still result in a default
        // imagery layer being installed. If the user explicitly selected a basemap
        // (google_xyz/google_official/osm/grid/photorealistic-only), ensure it actually
        // becomes the visible base layer.
        try {
          if (forcedBaseLayer === false) {
            try {
              viewer.imageryLayers.removeAll(true)
            } catch (_) {
              // ignore
            }
          } else if (forcedBaseProvider) {
            try {
              viewer.imageryLayers.removeAll(true)
            } catch (_) {
              // ignore
            }
            try {
              const layer = viewer.imageryLayers.addImageryProvider(forcedBaseProvider, 0)
              try {
                layer.alpha = 1.0
              } catch (_) {
                // ignore
              }
            } catch (_) {
              // ignore
            }
          }
        } catch (_) {
          // ignore
        }

        // Cesium can otherwise fire a large burst of parallel tile requests while
        // zooming/dragging, which is a common trigger for intermittent proxy-level
        // 502/504 in real remote deployments.
        try {
          const maxPerServer = Number(import.meta.env.VITE_CESIUM_MAX_REQUESTS_PER_SERVER || 8)
          const maxTotal = Number(import.meta.env.VITE_CESIUM_MAX_REQUESTS_TOTAL || 64)
          if (Cesium?.RequestScheduler) {
            Cesium.RequestScheduler.throttleRequests = true
            if (Number.isFinite(maxPerServer) && maxPerServer > 0) {
              Cesium.RequestScheduler.maximumRequestsPerServer = maxPerServer
            }
            if (Number.isFinite(maxTotal) && maxTotal > 0) {
              Cesium.RequestScheduler.maximumRequests = maxTotal
            }
          }
        } catch (_) {
          // ignore
        }

        // If we don't have an Ion token, the grid is only a last-resort visual fallback.
        // Add a real-world basemap (OSM) above it so users never see a blank/white globe.
        // NOTE: some client networks cannot reach public OSM tile domains (timeouts).
        // In production we prefer proxying OSM through our own /api endpoint.
        try {
          if (!hasIonToken) {
            const osmProxyFlag = String(import.meta.env.VITE_OSM_PROXY || '').trim()
            const useOsmProxy = (osmProxyFlag === '1') || (import.meta.env.PROD && osmProxyFlag !== '0')
            const osmBaseUrl = useOsmProxy ? '/api/basemap/osm/' : 'https://a.tile.openstreetmap.org/'
            const osmProvider = new Cesium.OpenStreetMapImageryProvider({
              // Use default OSM tile endpoint; keep it explicit for clarity.
              url: osmBaseUrl
            })
            const osmLayer = viewer.imageryLayers.addImageryProvider(osmProvider, 0)
            osmLayer.alpha = 1.0
          }
        } catch (_) {
          // ignore
        }
        
        // 光照：演示/开发阶段默认关闭，避免“黑夜=看不见地球”的经典坑
        viewer.scene.globe.enableLighting = (import.meta.env.VITE_ENABLE_LIGHTING === '1')
        // 强制确保 globe 可见（防止外部逻辑误关导致“无形地球”）
        viewer.scene.globe.show = true
        try {
          viewer.scene.skyAtmosphere.show = true
        } catch (_) {
          // ignore
        }
        viewer.scene.fog.enabled = true
        viewer.scene.fog.density = 0.0002
        
        // 初始相机位置
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(
            props.initialLocation.lon,
            props.initialLocation.lat,
            props.initialLocation.height
          ),
          orientation: {
            heading: Cesium.Math.toRadians(0.0),
            pitch: Cesium.Math.toRadians(-45.0),
            roll: 0.0
          }
        })
        
        // 相机移动事件
        viewer.camera.moveEnd.addEventListener(() => {
          const position = viewer.camera.positionCartographic
          emit('camera-moved', {
            lat: Cesium.Math.toDegrees(position.latitude),
            lon: Cesium.Math.toDegrees(position.longitude),
            height: position.height
          })

          // Ensure we update map center after any flight/drag ends.
          try {
            _emitMapCenter()
          } catch (_) {
            // ignore
          }

          try {
            _updatePhotorealisticTilesetVisibility()
          } catch (_) {
            // ignore
          }
        })

        // Real-time "screen center" updates while the user drags/zooms.
        // Use requestAnimationFrame throttling to avoid spamming Vue.
        centerTick = () => {
          if (centerRafPending) return
          centerRafPending = true
          try {
            requestAnimationFrame(() => {
              centerRafPending = false
              _emitMapCenter()
              _updatePhotorealisticTilesetVisibility()
            })
          } catch (_) {
            centerRafPending = false
          }
        }
        viewer.camera.changed.addEventListener(centerTick)

        // 地形/影像 tile 加载进度（辅助判断是否在持续请求）
        const onTileProgress = (remaining) => {
          emit('tile-load-progress', {
            remaining,
            ts: Date.now()
          })
        }
        viewer.scene.globe.tileLoadProgressEvent.addEventListener(onTileProgress)
        tileLoadUnsub = () => {
          try {
            viewer.scene.globe.tileLoadProgressEvent.removeEventListener(onTileProgress)
          } catch (_) {
            // ignore
          }
        }
        
        // Mark viewer as ready immediately after core Cesium initialization.
        // IMPORTANT: do NOT block readiness on network-heavy, optional assets
        // (photorealistic tiles, etc). Restricted networks can hang those requests.
        loading.value = false
        emit('viewer-ready', viewer)

        // Initial center emit.
        try {
          _emitMapCenter()
        } catch (_) {
          // ignore
        }

        // Click handler for 3D picking & point inspection
        try {
          if (viewer?.scene?.canvas) {
            clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
            clickHandler.setInputAction((movement) => {
              if (!viewer || disposed) return
              try {
                let cartesian = null
                if (viewer.scene.pickPositionSupported) {
                  cartesian = viewer.scene.pickPosition(movement.position)
                }
                if (!cartesian) {
                  const ray = viewer.camera.getPickRay(movement.position)
                  if (ray) {
                    cartesian = viewer.scene.globe.pick(ray, viewer.scene)
                  }
                }
                if (cartesian) {
                  const carto = Cesium.Cartographic.fromCartesian(cartesian)
                  const lon = Cesium.Math.toDegrees(carto.longitude)
                  const lat = Cesium.Math.toDegrees(carto.latitude)
                  emit('map-click', { lat, lon, height: carto.height })
                }
              } catch (_) {
                // ignore
              }
            }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
          }
        } catch (_) {
          // ignore
        }

        // Optional 3D buildings / photorealistic 3D tiles (requires Ion token + network)
        // Load asynchronously so it never blocks viewer-ready.
        try {
          const loadPhotorealisticAsync = async () => {
            if (!viewer || disposed) return
            if (!hasIonToken) return

            // Escape hatch: allow disabling photorealistic tiles from URL for demos
            // when Google/Cesium upstream is rate-limited (429) or blocked.
            try {
              const sp = new URLSearchParams(String(window?.location?.search || ''))
              const v = String(sp.get('photorealistic') || sp.get('pr') || '').trim().toLowerCase()
              const off = v === '0' || v === 'off' || v === 'false'
              if (off) return
            } catch (_) {
              // ignore
            }

            const photorealisticAssetId = Number(import.meta.env.VITE_ION_PHOTOREALISTIC_ASSET_ID || '')
            const enablePhotorealistic = Number.isFinite(photorealisticAssetId) && photorealisticAssetId > 0

            if (!enablePhotorealistic) {
              try {
                viewer.scene.primitives.add(Cesium.createOsmBuildings())
              } catch (_) {
                // ignore
              }
              return
            }

            let tileset = null
            try {
              // Give Ion resource resolution / tileset bootstrap a bounded time budget.
              if (Cesium?.Cesium3DTileset?.fromIonAssetId) {
                tileset = await _withTimeout(Cesium.Cesium3DTileset.fromIonAssetId(photorealisticAssetId), 12000, 'ion_tileset')
              } else {
                const resource = await _withTimeout(Cesium.IonResource.fromAssetId(photorealisticAssetId), 8000, 'ion_resource')
                tileset = await _withTimeout(Cesium.Cesium3DTileset.fromUrl(resource), 12000, 'tileset_url')
              }
            } catch (e) {
              console.warn(
                '[OneEarth Cesium] photorealistic tileset load skipped (offline/restricted network). ' +
                  'Tip: add ?photorealistic=off to disable during demos.',
                e
              )
              return
            }

            if (!tileset || !viewer || disposed) return

            try {
              viewer.scene.primitives.add(tileset)
              photorealisticTileset = tileset
              photorealisticTilesetBaseStyle = tileset.style || null
              lastAppliedTilesetShow = null
              lastAppliedTilesetStyle = null
            } catch (_) {
              // ignore
            }

            try {
              viewer.scene.globe.depthTestAgainstTerrain = false
            } catch (_) {
              // ignore
            }

            try {
              _updatePhotorealisticTilesetVisibility()
            } catch (_) {
              // ignore
            }
          }

          void loadPhotorealisticAsync()
        } catch (_) {
          // ignore
        }

        // 仍保留第 0 层底图的 error 监听，便于 HUD 定位瓦片失败原因。
        try {
          const baseLayer = viewer.imageryLayers.get(0)
          const baseProvider = baseLayer && baseLayer.imageryProvider
          if (baseProvider && baseProvider.errorEvent) {
            const onBaseError = (err) => {
              emit('imagery-error', {
                layer: 'fallback',
                ts: Date.now(),
                message: err?.message || String(err)
              })
            }
            baseProvider.errorEvent.addEventListener(onBaseError)
            ionBaseProviderUnsub = () => {
              try {
                baseProvider.errorEvent.removeEventListener(onBaseError)
              } catch (_) {
                // ignore
              }
            }
          }
        } catch (_) {
          // ignore
        }
        
      } catch (error) {
        console.error('Cesium初始化失败:', error)
        loading.value = false
        loadingText.value = '初始化失败: ' + (error?.message || String(error))
      }
    }

    function _restoreHiddenBaseLayers() {
      if (!viewer) return
      if (!hiddenBaseLayers || !hiddenBaseLayers.length) return
      try {
        hiddenBaseLayers.forEach((layer) => {
          try {
            layer.show = true
          } catch (_) {
            // ignore
          }
        })
      } finally {
        hiddenBaseLayers = []
      }
    }

    function _hideNonManagedBaseLayers() {
      if (!viewer) return
      hiddenBaseLayers = []
      const layers = viewer.imageryLayers
      const n = layers.length
      for (let i = 0; i < n; i++) {
        const layer = layers.get(i)
        if (!layer) continue
        if (layer === currentBasemapLayer) continue
        if (layer === currentAILayer) continue
        // Hide anything else (Ion default, OSM fallback, grid, etc) so the managed basemap becomes visible.
        try {
          if (layer.show !== false) {
            layer.show = false
            hiddenBaseLayers.push(layer)
          }
        } catch (_) {
          // ignore
        }
      }
    }

    function _getBasemapInsertIndex() {
      if (!viewer) return 0
      const layers = viewer.imageryLayers
      const n = layers.length

      // Insert basemap ABOVE any default base layers (Ion/OSM/Grid), but keep it
      // BELOW the AI overlay layer (so AI always stays on top).
      if (currentAILayer) {
        try {
          const aiIndex = layers.indexOf(currentAILayer)
          if (typeof aiIndex === 'number' && aiIndex >= 0) return aiIndex
        } catch (_) {
          // ignore
        }
      }

      return n
    }

    /**
     * 加载/替换底图图层（推荐：Sentinel-2 真彩底图）
     * - 始终插入到 imageryLayers 的 index=0，确保 split-compare 左侧对比稳定
     * - 若底图瓦片偶发失败（后端会返回透明 PNG），仍可透出更底层的 basemap（Ion/OSM/Grid）
     */
    function loadBasemapLayer(tileUrl, opacity = 1.0) {
      if (!viewer) return
      if (!tileUrl) return

      if (currentBasemapLayer) {
        try {
          viewer.imageryLayers.remove(currentBasemapLayer)
        } catch (_) {
          // ignore
        }
        currentBasemapLayer = null
      }
      if (currentBasemapProviderUnsub) {
        currentBasemapProviderUnsub()
        currentBasemapProviderUnsub = null
      }

      const provider = new Cesium.UrlTemplateImageryProvider({
        url: tileUrl,
        tileWidth: 256,
        tileHeight: 256,
        minimumLevel: 0,
        tileDiscardPolicy: new Cesium.NeverTileDiscardPolicy(),
        maximumLevel: 18
      })

      const onProviderError = (tileError) => {
        emit('imagery-error', {
          layer: 'basemap',
          ts: Date.now(),
          message: tileError?.message || String(tileError),
          x: tileError?.x,
          y: tileError?.y,
          level: tileError?.level,
          timesRetried: tileError?.timesRetried
        })

        // If the basemap is genuinely failing (HTTP errors), drop it immediately.
        // We intentionally keep Ion/OSM/Grid layers underneath, so users never see
        // a blank globe even when Sentinel-2 is slow or fails.
        try {
          clearBasemapLayer()
        } catch (_) {
          // ignore
        }
      }
      try {
        provider.errorEvent.addEventListener(onProviderError)
        currentBasemapProviderUnsub = () => {
          try {
            provider.errorEvent.removeEventListener(onProviderError)
          } catch (_) {
            // ignore
          }
        }
      } catch (_) {
        // ignore
      }

      // Insert above the underlying basemap, but below the AI overlay.
      const insertIndex = _getBasemapInsertIndex()
      currentBasemapLayer = viewer.imageryLayers.addImageryProvider(provider, insertIndex)
      currentBasemapLayer.alpha = Math.max(0.0, Math.min(1.0, Number(opacity) || 1.0))
    }

    function clearBasemapLayer() {
      if (!viewer) return
      if (currentBasemapLayer) {
        try {
          viewer.imageryLayers.remove(currentBasemapLayer)
        } catch (_) {
          // ignore
        }
        currentBasemapLayer = null
      }
      if (currentBasemapProviderUnsub) {
        currentBasemapProviderUnsub()
        currentBasemapProviderUnsub = null
      }
    }

    function _emitMapCenter() {
      if (!viewer) return
      const canvas = viewer.scene?.canvas
      if (!canvas) return

      const w = canvas.clientWidth || canvas.width
      const h = canvas.clientHeight || canvas.height
      if (!w || !h) return

      const centerPx = new Cesium.Cartesian2(w / 2, h / 2)
      const ellipsoid = viewer.scene?.globe?.ellipsoid || Cesium.Ellipsoid.WGS84
      const cartesian = viewer.camera.pickEllipsoid(centerPx, ellipsoid)
      if (!cartesian) return

      const carto = Cesium.Cartographic.fromCartesian(cartesian)
      const lat = Cesium.Math.toDegrees(carto.latitude)
      const lon = Cesium.Math.toDegrees(carto.longitude)

      // Only emit if changed enough (avoid noisy updates).
      const eps = 1e-6
      if (
        lastCenterLat !== null &&
        lastCenterLon !== null &&
        Math.abs(lat - lastCenterLat) < eps &&
        Math.abs(lon - lastCenterLon) < eps
      ) {
        return
      }
      lastCenterLat = lat
      lastCenterLon = lon

      emit('map-center-changed', { lat, lon, ts: Date.now() })
    }
    
    /**
     * 加载 AI 图层
     */
    function loadAILayer(tileUrl, opacity = 0.95, options = {}) {
      if (!viewer) return

      isAILayerActive = true
      _updatePhotorealisticTilesetVisibility()
      
      // 移除旧图层
      if (currentAILayer) {
        viewer.imageryLayers.remove(currentAILayer)
      }
      if (currentAIProviderUnsub) {
        currentAIProviderUnsub()
        currentAIProviderUnsub = null
      }
      
      let rect = undefined
      if (options?.bounds && Array.isArray(options.bounds) && options.bounds.length === 4) {
        try {
          rect = Cesium.Rectangle.fromDegrees(
            options.bounds[0],
            options.bounds[1],
            options.bounds[2],
            options.bounds[3]
          )
        } catch (_) {
          // ignore
        }
      }

      // 添加新图层
      const provider = new Cesium.UrlTemplateImageryProvider({
        url: tileUrl,
        tileWidth: 256,
        tileHeight: 256,
        minimumLevel: 0,
        maximumLevel: 18,
        rectangle: rect,
        // 透明 PNG 也应被视为“成功瓦片”，否则 Cesium 可能持续丢弃并重试
        tileDiscardPolicy: new Cesium.NeverTileDiscardPolicy()
      })

      const onProviderError = (tileError) => {
        // Cesium 的 error 对象在不同版本字段略有差异，这里做尽量鲁棒的采集
        emit('imagery-error', {
          layer: 'ai',
          ts: Date.now(),
          message: tileError?.message || String(tileError),
          x: tileError?.x,
          y: tileError?.y,
          level: tileError?.level,
          timesRetried: tileError?.timesRetried
        })
      }
      provider.errorEvent.addEventListener(onProviderError)
      currentAIProviderUnsub = () => {
        try {
          provider.errorEvent.removeEventListener(onProviderError)
        } catch (_) {
          // ignore
        }
      }
      
      currentAILayer = viewer.imageryLayers.addImageryProvider(provider)
      if (fadeTimer) {
        clearInterval(fadeTimer)
        fadeTimer = null
      }

      if (options?.fadeIn) {
        currentAILayer.alpha = 0.0
        fadeTimer = setInterval(() => {
          if (!currentAILayer) {
            clearInterval(fadeTimer)
            fadeTimer = null
            return
          }
          const next = currentAILayer.alpha + 0.06
          if (next >= opacity) {
            currentAILayer.alpha = opacity
            clearInterval(fadeTimer)
            fadeTimer = null
          } else {
            currentAILayer.alpha = next
          }
        }, 50)
      } else {
        currentAILayer.alpha = opacity
      }
      _updatePhotorealisticTilesetVisibility()
    }

    function clearAILayer() {
      if (!viewer) return
      if (fadeTimer) {
        clearInterval(fadeTimer)
        fadeTimer = null
      }
      if (currentAILayer) {
        try {
          viewer.imageryLayers.remove(currentAILayer)
        } catch (_) {
          // ignore
        }
        currentAILayer = null
      }
      if (currentAIProviderUnsub) {
        currentAIProviderUnsub()
        currentAIProviderUnsub = null
      }

      isAILayerActive = false
      _updatePhotorealisticTilesetVisibility()
    }

    function setAILayerVisible(visible) {
      if (!viewer) return
      if (currentAILayer) {
        currentAILayer.show = !!visible
      }

      isAILayerActive = !!visible
      _updatePhotorealisticTilesetVisibility()
    }

    function enableSplitCompare(enabled, position = 0.5) {
      if (!viewer) return

      const baseLayer = currentBasemapLayer || viewer.imageryLayers.get(0)
      const splitPos = Math.min(0.98, Math.max(0.02, Number(position) || 0.5))

      if (enabled) {
        viewer.scene.splitPosition = splitPos
        // Keep the basemap visible on BOTH sides. Only split the AI overlay.
        // Otherwise, transparent AI pixels reveal Cesium's clearColor (often blue),
        // which looks like a "blue background" behind the AI layer.
        if (baseLayer) baseLayer.splitDirection = Cesium.SplitDirection.NONE
        if (currentAILayer) currentAILayer.splitDirection = Cesium.SplitDirection.RIGHT
      } else {
        if (baseLayer) baseLayer.splitDirection = Cesium.SplitDirection.NONE
        if (currentAILayer) currentAILayer.splitDirection = Cesium.SplitDirection.NONE
      }
    }

    function setSplitPosition(position = 0.5) {
      if (!viewer) return
      const splitPos = Math.min(0.98, Math.max(0.02, Number(position) || 0.5))
      viewer.scene.splitPosition = splitPos
    }
    
    
    /**
     * 飞行到指定地点
     */
    function flyTo(location, duration = 3.0, onComplete = null) {
      if (!viewer) return

      const lon = Number(location?.lon)
      const lat = Number(location?.lat)
      const range = Number(location?.height || 15000)
      const headingDeg = (location?.heading_deg === undefined || location?.heading_deg === null)
        ? 0.0
        : Number(location.heading_deg)
      const pitchDeg = (location?.pitch_deg === undefined || location?.pitch_deg === null)
        ? -45.0
        : Number(location.pitch_deg)

      const easingKey = String(location?.easing || '').trim()
      const easing = (() => {
        if (!easingKey) return undefined
        const k = easingKey.toLowerCase()
        const map = {
          cubicinout: Cesium.EasingFunction.CUBIC_IN_OUT,
          cubicin: Cesium.EasingFunction.CUBIC_IN,
          cubicout: Cesium.EasingFunction.CUBIC_OUT,
          quadraticout: Cesium.EasingFunction.QUADRATIC_OUT,
          quadraticinout: Cesium.EasingFunction.QUADRATIC_IN_OUT,
        }
        return map[k]
      })()

      // Important: when using a tilted pitch, the camera "destination" is NOT the same as the
      // "look-at" center. Using flyToBoundingSphere keeps the target coordinate centered.
      try {
        const center = Cesium.Cartesian3.fromDegrees(lon, lat, 0.0)
        const sphere = new Cesium.BoundingSphere(center, 200.0)
        viewer.camera.flyToBoundingSphere(sphere, {
          duration: duration,
          offset: new Cesium.HeadingPitchRange(
            Cesium.Math.toRadians(headingDeg),
            Cesium.Math.toRadians(pitchDeg),
            range
          ),
          ...(easing ? { easingFunction: easing } : {}),
          complete: () => {
            try {
              onComplete && onComplete()
            } catch (_) {
              // ignore
            }
          }
        })
        return
      } catch (_) {
        // Fallback to plain flyTo if something goes wrong
      }

      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, range),
        orientation: {
          heading: Cesium.Math.toRadians(headingDeg),
          pitch: Cesium.Math.toRadians(pitchDeg),
          roll: 0.0
        },
        duration: duration,
        ...(easing ? { easingFunction: easing } : {}),
        complete: () => {
          try {
            onComplete && onComplete()
          } catch (_) {
            // ignore
          }
        }
      })
    }

    function startGlobalRotation() {
      if (!viewer) return

      // Fly to a global view and start a slow rotation
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(105.0, 35.0, 20000000.0),
        duration: 2.0
      })

      if (!rotationTick) {
        rotationTick = () => {
          try {
            viewer.scene.camera.rotate(Cesium.Cartesian3.UNIT_Z, 0.0005)
          } catch (_) {
            // ignore
          }
        }
        viewer.clock.onTick.addEventListener(rotationTick)
      }
    }

    function stopGlobalRotation() {
      if (!viewer) return
      if (rotationTick) {
        try {
          viewer.clock.onTick.removeEventListener(rotationTick)
        } catch (_) {
          // ignore
        }
        rotationTick = null
      }
    }

    function setGlobeVisible(visible) {
      if (!viewer) return
      try {
        if (viewer?.scene?.globe) viewer.scene.globe.show = !!visible
      } catch (_) {
        // ignore
      }
    }

    // Act2 cinematic preset (Storyboard A: dawn terminator / edge-of-space)
    function applyAct2StoryboardPresetA(options = {}) {
      if (!viewer) return false

      const opts = options && typeof options === 'object' ? options : {}
      const iso = String(opts.timeIso || '2026-03-03T10:30:00Z').trim() || '2026-03-03T10:30:00Z'

      try {
        if (viewer.scene?.globe) {
          viewer.scene.globe.enableLighting = true
        }
      } catch (_) {
        // ignore
      }

      try {
        if (viewer.scene?.skyAtmosphere) {
          viewer.scene.skyAtmosphere.show = true
          // Stronger techy rim glow (best-effort; values can be tuned later)
          viewer.scene.skyAtmosphere.hueShift = -0.1
          viewer.scene.skyAtmosphere.saturationShift = 0.3
          viewer.scene.skyAtmosphere.brightnessShift = 0.4
        }
      } catch (_) {
        // ignore
      }

      try {
        const targetTime = Cesium.JulianDate.fromDate(new Date(iso))
        viewer.clock.currentTime = targetTime
        viewer.clock.shouldAnimate = false
      } catch (_) {
        // ignore
      }

      return true
    }
    
    /**
     * 设置 AI 图层透明度
     */
    function setAILayerOpacity(opacity) {
      if (currentAILayer) {
        currentAILayer.alpha = opacity
      }
    }

    /**
     * 3D InSAR 靶向锚标与视准激光束高亮 (Inspection Beacon)
     */
    function setInspectionBeacon(opts) {
      if (!viewer || disposed || !opts || opts.lat === undefined || opts.lon === undefined) return
      clearInspectionBeacon()
      try {
        const lon = Number(opts.lon)
        const lat = Number(opts.lat)
        const h = Number(opts.height || 0)
        const isCritical = opts.riskLevel === 'critical'
        const beaconColor = isCritical ? Cesium.Color.RED : Cesium.Color.CYAN
        const beamColor = isCritical
          ? new Cesium.Color(1.0, 0.23, 0.19, 0.6)
          : new Cesium.Color(0.0, 0.96, 1.0, 0.6)

        inspectionBeaconEntity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(lon, lat, h),
          point: {
            pixelSize: 10,
            color: beaconColor,
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          },
          polyline: {
            positions: [
              Cesium.Cartesian3.fromDegrees(lon, lat, h),
              Cesium.Cartesian3.fromDegrees(lon, lat, h + 220)
            ],
            width: 2.5,
            material: beamColor
          },
          label: {
            text: opts.label || '🎯 InSAR 靶向锚点',
            font: '11px ui-monospace, SFMono-Regular, monospace, sans-serif',
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 3,
            pixelOffset: new Cesium.Cartesian2(0, -32),
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        })
      } catch (_) {
        // ignore
      }
    }

    function clearInspectionBeacon() {
      if (viewer && inspectionBeaconEntity) {
        try {
          viewer.entities.remove(inspectionBeaconEntity)
        } catch (_) {
          // ignore
        }
        inspectionBeaconEntity = null
      }
    }

    /**
     * 加载 InSAR 实测永久散射体 (PS) 靶向观测点图层
     */
    function loadInsarPoints(points = []) {
      clearInsarPoints()
      if (!viewer || disposed || !Array.isArray(points) || !points.length) return
      try {
        for (const pt of points) {
          const lon = Number(pt.lon)
          const lat = Number(pt.lat)
          const h = Number(pt.height || 10)
          const v = Number(pt.velocity_mm_yr || 0)
          const isCritical = pt.risk_level === 'critical' || v < -20
          const isWarning = pt.risk_level === 'warning' || (v >= -20 && v < -10)
          const color = isCritical
            ? Cesium.Color.RED
            : (isWarning ? Cesium.Color.ORANGE : Cesium.Color.YELLOW)

          const ent = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(lon, lat, h),
            point: {
              pixelSize: 8,
              color: color,
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 1.5,
              disableDepthTestDistance: Number.POSITIVE_INFINITY
            },
            label: {
              text: `${pt.name}\n${v > 0 ? '+' : ''}${v} mm/yr`,
              font: '10px ui-monospace, SFMono-Regular, monospace, sans-serif',
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 3,
              pixelOffset: new Cesium.Cartesian2(0, -24),
              disableDepthTestDistance: Number.POSITIVE_INFINITY
            }
          })
          ent._insarData = pt
          insarPointEntities.push(ent)
        }
      } catch (err) {
        console.warn('Failed to load InSAR point layer:', err)
      }
    }

    function clearInsarPoints() {
      if (viewer && insarPointEntities.length) {
        try {
          for (const ent of insarPointEntities) {
            viewer.entities.remove(ent)
          }
        } catch (_) {
          // ignore
        }
        insarPointEntities = []
      }
    }

    function _makeFootprint(lon, lat, wMeters, dMeters) {
      const dlat = dMeters / 110540
      const dlon = wMeters / (111320 * Math.max(0.2, Math.cos(lat * Math.PI / 180)))
      const hw = dlon / 2
      const hd = dlat / 2
      return [
        lon - hw, lat - hd,
        lon + hw, lat - hd,
        lon + hw, lat + hd,
        lon - hw, lat + hd,
      ]
    }

    // 旗舰单体 → 通用古建 .glb 模型（台门/多进院落/厅堂），替代平顶方块
    const HERITAGE_MODELS = {
      'SX-YC-ZP-08': { modelKey: 'taimen', anchors: 'heritage_taimen_courtyard_anchors.json', heading: 18, prefix: '正厅_' },
      'JH-DY-LZ-001': { modelKey: 'complex', anchors: 'heritage_complex_multicourt_anchors.json', heading: 90, prefix: '正厅_' },
      'JH-DY-LZ-002': { modelKey: 'hall', anchors: 'heritage_hall_xieshan_anchors.json', heading: 90, prefix: '厅堂_' },
    }

    function _anchorItemsFor(conf, pt) {
      const weak = pt?.weak_points || []
      const items = []
      const seen = new Set()
      for (const wp of weak) {
        const part = wp.part
        const key = part === '屋脊' ? `${conf.prefix}屋脊`
          : part === '檐口' ? `${conf.prefix}檐口`
          : part === '翼角' ? `${conf.prefix}翼角_东南`
          : part === '山墙' ? `${conf.prefix}山墙_东`
          : null
        if (!key || seen.has(key)) continue
        seen.add(key)
        items.push({
          key,
          label: part,
          value: `${wp.level === 'severe' ? '−3.70' : wp.level === 'moderate' ? '−2.85' : '+1.42'} kPa`,
          level: wp.level === 'severe' ? 'severe' : wp.level === 'moderate' ? 'moderate' : 'watch',
        })
      }
      return items
    }

    /**
     * 加载 CH9 古建单体 3D 白模：旗舰单体用通用 .glb 模型，其余用挤出白模，
     * 按 risk_level 荧光染色。
     */
    function loadHeritageBuildings(points = []) {
      clearHeritageBuildings()
      if (!viewer || disposed || !Array.isArray(points) || !points.length) return
      try {
        for (const pt of points) {
          const lon = Number(pt.centroid?.[0])
          const lat = Number(pt.centroid?.[1])
          if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue
          const risk = String(pt.risk_level || '')
          const isCandidate = !!pt.is_candidate
          const conf = HERITAGE_MODELS[pt.building_id]

          if (conf) {
            // 旗舰单体：加载 .glb 模型 + MIX 风险染色 + 呼吸灯
            const riskLevel = risk === 'unstable' ? 'unstable' : risk === 'moderate' ? 'moderate' : 'stable'
            let ent = null
            try {
              ent = addHeritageModel(viewer, {
                buildingId: pt.building_id,
                name: pt.name,
                position: [lon, lat, 0],
                modelKey: conf.modelKey,
                heading: conf.heading,
                scale: 1.0,
                riskLevel,
                breathing: riskLevel === 'unstable' || riskLevel === 'moderate',
                blendAmount: 0.5,
              })
            } catch (e) {
              console.warn('模型加载失败，回退挤出白模:', e)
              ent = null
            }
            if (ent) {
              ent._heritageData = pt
              heritageBuildingEntities.push(ent)
              // 异步挂载部位锚点
              fetch(`/assets/models/${conf.anchors}`)
                .then((r) => r.json())
                .then((a) => {
                  try {
                    bindAnchorLabels(viewer, {
                      buildingId: pt.building_id,
                      position: [lon, lat, 0],
                      heading: conf.heading,
                      scale: 1.0,
                      anchors: a.anchors_local_m,
                      anchorItems: _anchorItemsFor(conf, pt),
                    })
                  } catch (e) { console.warn('锚点绑定失败:', e) }
                })
                .catch(() => {})
              continue
            }
          }

          const baseColor = isCandidate ? Cesium.Color.GOLD
            : risk === 'unstable' ? Cesium.Color.RED
            : risk === 'moderate' ? Cesium.Color.ORANGE
            : Cesium.Color.CYAN
          const alpha = isCandidate ? 0.9
            : risk === 'unstable' ? 0.85
            : risk === 'moderate' ? 0.6
            : 0.22
          const height = isCandidate ? 6 : (risk === 'unstable' ? 16 : risk === 'moderate' ? 12 : 9)

          const footprint = _makeFootprint(lon, lat, isCandidate ? 22 : 18, isCandidate ? 16 : 12)
          const ent = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(footprint),
              extrudedHeight: height,
              material: baseColor.withAlpha(alpha),
              outline: true,
              outlineColor: Cesium.Color.WHITE.withAlpha(0.45),
            },
            label: {
              text: `🏯 ${pt.name || ''}`,
              font: '11px ui-monospace, SFMono-Regular, monospace, sans-serif',
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 3,
              pixelOffset: new Cesium.Cartesian2(0, -26),
              disableDepthTestDistance: Number.POSITIVE_INFINITY
            }
          })
          ent._heritageData = pt
          heritageBuildingEntities.push(ent)
        }
        _startHeritagePulse()
      } catch (err) {
        console.warn('Failed to load heritage building layer:', err)
      }
    }

    function _startHeritagePulse() {
      if (heritagePulseTimer) return
      let phase = 0
      heritagePulseTimer = setInterval(() => {
        phase += 0.14
        const pulse = 0.5 + 0.5 * Math.sin(phase)
        try {
          for (const ent of heritageBuildingEntities) {
            if (ent?._heritageData?.risk_level !== 'unstable') continue
            if (ent.polygon?.material?.color) {
              ent.polygon.material.color = Cesium.Color.RED.withAlpha(0.35 + 0.55 * pulse)
            }
          }
        } catch (_) {
          // ignore
        }
      }, 80)
    }

    function clearHeritageBuildings() {
      if (heritagePulseTimer) {
        clearInterval(heritagePulseTimer)
        heritagePulseTimer = null
      }
      if (viewer && heritageBuildingEntities.length) {
        try {
          for (const ent of heritageBuildingEntities) {
            viewer.entities.remove(ent)
          }
        } catch (_) {
          // ignore
        }
        heritageBuildingEntities = []
      }
    }

    function _heritageLevelColor(level, type) {
      if (level === 'world_heritage') return Cesium.Color.GOLD
      if (level === 'national') return Cesium.Color.fromCssColorString('#FF7A45')
      if (type === 'temple' || type === 'shrine' || type === 'pagoda') return Cesium.Color.fromCssColorString('#5DAE8B')
      return Cesium.Color.CYAN
    }

    /**
     * 动态生成全息质感的聚合点 Canvas 纹理（文物金底座 + 呼吸外环 + 高亮数字）。
     */
    function createClusterHologram(count) {
      const size = count > 1000 ? 90 : (count > 100 ? 75 : 60)
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')
      const center = size / 2
      const radius = center - 8

      // 外圈文物金发光光晕
      ctx.shadowBlur = 15
      ctx.shadowColor = 'rgba(240, 196, 104, 0.8)'
      // 半透明暗色底座（屏蔽底图穿透）
      ctx.beginPath()
      ctx.arc(center, center, radius, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(10, 15, 25, 0.78)'
      ctx.fill()
      // 科技感主圆环
      ctx.lineWidth = 2.5
      ctx.strokeStyle = 'rgba(240, 196, 104, 0.9)'
      ctx.stroke()
      // 预警橙外环
      ctx.beginPath()
      ctx.arc(center, center, radius + 3, 0, Math.PI * 2)
      ctx.lineWidth = 1.5
      ctx.strokeStyle = 'rgba(226, 61, 40, 0.6)'
      ctx.stroke()

      ctx.shadowBlur = 0
      ctx.font = `bold ${count > 100 ? 18 : 20}px "DIN Alternate", "Rajdhani", "Oswald", sans-serif`
      ctx.fillStyle = '#FFFFFF'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      const displayCount = count >= 10000 ? (count / 10000).toFixed(1) + 'w' : String(count)
      ctx.fillText(displayCount, center, center + 1)

      return canvas.toDataURL()
    }

    /**
     * 加载 CH9 真实开放数据点云（L1 世界遗产 / L2 国保 / 本地 OSM）。
     * 使用独立 CustomDataSource + EntityCluster 做 LOD 聚合，避免万级点位卡顿。
     * 颜色分级：world_heritage=金 / national=橙红 / 其他=青。
     */
    function loadHeritagePointCloud(points = [], opts = {}) {
      clearHeritagePointCloud()
      if (!viewer || disposed || !Array.isArray(points) || !points.length) return
      try {
        const ds = new Cesium.CustomDataSource('ch9-heritage-points')
        const colorFn = opts.colorBy === 'national'
          ? () => Cesium.Color.fromCssColorString('#FF7A45')
          : _heritageLevelColor

        ds.entities.suspendEvents()
        for (const pt of points) {
          const lon = Number(pt.lon)
          const lat = Number(pt.lat)
          if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue
          const color = colorFn(pt.level, pt.type)
          ds.entities.add({
            position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
            point: {
              pixelSize: 5,
              color: color,
              outlineColor: Cesium.Color.WHITE.withAlpha(0.35),
              outlineWidth: 1,
              disableDepthTestDistance: Number.POSITIVE_INFINITY
            }
          })
        }
        ds.entities.resumeEvents()
        ds.clustering.enabled = true
        ds.clustering.pixelRange = 38
        ds.clustering.minimumClusterSize = 3
        // 全息星火聚合：拦截 clusterEvent，用动态 Canvas 徽章替换默认白色文本标签
        ds.clustering.clusterEvent.addEventListener((clusteredEntities, cluster) => {
          try {
            cluster.label.show = false
            cluster.billboard.show = true
            cluster.billboard.image = createClusterHologram(clusteredEntities.length)
            cluster.billboard.verticalOrigin = Cesium.VerticalOrigin.CENTER
            cluster.billboard.scaleByDistance = new Cesium.NearFarScalar(1.5e2, 1.2, 1.5e7, 0.6)
          } catch (_) {
            // ignore
          }
        })
        viewer.dataSources.add(ds)
        heritagePointDataSource = ds
      } catch (err) {
        console.warn('Failed to load heritage point cloud:', err)
      }
    }

    function clearHeritagePointCloud() {
      if (viewer && heritagePointDataSource) {
        try {
          viewer.dataSources.remove(heritagePointDataSource)
        } catch (_) {
          // ignore
        }
        heritagePointDataSource = null
      }
    }

    /**
     * 暗黑电影模式：压暗底图（baseColor）+ Bloom 泛光后处理，让预警锚点如霓虹发光。
     */
    function setCinematicMode(enabled) {
      if (!viewer) return
      if (enabled) {
        // 电影级打光：定向光 + 雾 + HDR + 暗环境（侧边栏暗黑 vs 地图大白天不再割裂）
        try { applyCinematicLighting(viewer) } catch (_) { /* ignore */ }
      } else {
        try {
          viewer.scene.globe.baseColor = Cesium.Color.WHITE
          viewer.scene.light = new Cesium.SunLight()
          viewer.scene.fog.enabled = false
          viewer.scene.highDynamicRange = false
          viewer.scene.globe.enableLighting = false
        } catch (_) { /* ignore */ }
      }
      // 适度压暗底图（不过暗，保证图层可读），凸显发光点位
      try {
        const base = viewer.imageryLayers.get(0)
        if (base) {
          base.brightness = enabled ? 0.55 : 1.0
          base.contrast = enabled ? 1.2 : 1.0
        }
      } catch (_) {
        // ignore
      }
      try {
        if (enabled && !cinematicBloomStage) {
          cinematicBloomStage = viewer.scene.postProcessStages.add(
            Cesium.PostProcessStageLibrary.createBloomStage()
          )
          cinematicBloomStage.uniforms.glowOnly = false
          cinematicBloomStage.uniforms.contrast = 140
          cinematicBloomStage.uniforms.brightness = -0.2
          cinematicBloomStage.uniforms.delta = 0.9
          cinematicBloomStage.uniforms.sigma = 3.8
          cinematicBloomStage.uniforms.stepSize = 4
        } else if (!enabled && cinematicBloomStage) {
          viewer.scene.postProcessStages.remove(cinematicBloomStage)
          cinematicBloomStage = null
        }
      } catch (_) {
        // ignore
      }
    }

    /**
     * 一镜到底 · 微观下潜：平滑飞至 CH9 三个靶场（绍兴/东阳/平遥）。
     */
    function performDive(targetKey) {
      if (!viewer) return
      const microTargets = {
        shaoxing: { lat: 30.002, lon: 120.581, height: 1200, pitch: -45, heading: 20 },
        dongyang: { lat: 29.283, lon: 120.241, height: 800, pitch: -30, heading: 90 },
        pingyao: { lat: 37.201, lon: 112.175, height: 2500, pitch: -60, heading: 0 },
      }
      const t = microTargets[targetKey]
      if (!t) return
      try {
        // 使目标坐标居中：从目标点沿 heading/pitch/range 反推相机位置，而非把相机放在目标点
        const center = Cesium.Cartesian3.fromDegrees(t.lon, t.lat, 0)
        const heading = Cesium.Math.toRadians(t.heading)
        const pitch = Cesium.Math.toRadians(t.pitch)
        const hpr = new Cesium.HeadingPitchRange(heading, pitch, t.height)
        const cameraPos = Cesium.Matrix4.getTranslation(
          Cesium.Transforms.headingPitchRollToFixedFrame(center, hpr),
          new Cesium.Cartesian3()
        )
        viewer.camera.flyTo({
          destination: cameraPos,
          orientation: { heading, pitch, roll: 0 },
          duration: 3.0,
          easingFunction: Cesium.EasingFunction.CUBIC_IN_OUT,
        })
      } catch (_) {
        // ignore
      }
    }

    function _windTrailMaterial(speed) {
      const color = Cesium.Color.CYAN.withAlpha(0.75)
      // Cesium 1.90+ 的移动拖尾材质为 PolylineTrailMaterialProperty；
      // 旧版 PolylineTrailLinkMaterialProperty 已移除，这里做多重回退。
      try {
        if (Cesium.PolylineTrailMaterialProperty) {
          return new Cesium.PolylineTrailMaterialProperty({
            color,
            trailLength: 0.4,
            period: 2.0 / (Number(speed) || 3),
          })
        }
      } catch (_) {
        // fall through
      }
      try {
        if (Cesium.PolylineGlowMaterialProperty) {
          return new Cesium.PolylineGlowMaterialProperty({ color, glowPower: 0.25 })
        }
      } catch (_) {
        // fall through
      }
      return color
    }

    /**
     * 加载 CH9-A 风载场景：风场动态流线 + FEA 薄弱点闪烁锚标。
     */
    function loadWindScene(scene = {}) {
      clearWindScene()
      if (!viewer || disposed) return
      const trails = Array.isArray(scene.trails) ? scene.trails : []
      const anchors = Array.isArray(scene.anchors) ? scene.anchors : []
      try {
        for (const t of trails) {
          const pts = (Array.isArray(t.points) ? t.points : []).map(
            (p) => Cesium.Cartesian3.fromDegrees(Number(p[0]), Number(p[1]), Number(p[2] || 40))
          )
          if (pts.length < 2) continue
          const ent = viewer.entities.add({
            polyline: {
              positions: pts,
              width: 2.5,
              material: _windTrailMaterial(Number(t.speed) || 3),
            },
          })
          windTrailEntities.push(ent)
        }
        for (const a of anchors) {
          const lon = Number(a.lon)
          const lat = Number(a.lat)
          if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue
          const severe = a.level === 'severe'
          const ent = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(lon, lat, Number(a.height || 16)),
            point: {
              pixelSize: severe ? 10 : 7,
              color: severe ? Cesium.Color.RED : Cesium.Color.ORANGE,
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 1.5,
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            },
            label: {
              text: `⚠️ ${a.part} | ${a.pressure_kpa} kPa | ${a.note}`,
              font: '12px ui-monospace, SFMono-Regular, monospace, sans-serif',
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 3,
              pixelOffset: new Cesium.Cartesian2(0, -30),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            },
          })
          feaAnchorEntities.push(ent)
        }
        _startFeaPulse()
      } catch (err) {
        console.warn('Failed to load wind scene:', err)
      }
    }

    function _startFeaPulse() {
      if (feaPulseTimer || !feaAnchorEntities.length) return
      let on = true
      feaPulseTimer = setInterval(() => {
        on = !on
        try {
          for (const ent of feaAnchorEntities) {
            if (ent.point) ent.point.pixelSize = on ? (ent.point.pixelSize >= 9 ? 11 : 9) : 5
          }
        } catch (_) {
          // ignore
        }
      }, 500)
    }

    function clearWindScene() {
      if (feaPulseTimer) {
        clearInterval(feaPulseTimer)
        feaPulseTimer = null
      }
      if (viewer) {
        try {
          for (const ent of windTrailEntities) viewer.entities.remove(ent)
          for (const ent of feaAnchorEntities) viewer.entities.remove(ent)
        } catch (_) {
          // ignore
        }
      }
      windTrailEntities = []
      feaAnchorEntities = []
    }

    return {
      cesiumContainer,
      creditContainer,
      loading,
      loadingText,
      loadAILayer,
      clearAILayer,
      loadBasemapLayer,
      clearBasemapLayer,
      setAILayerVisible,
      enableSplitCompare,
      setSplitPosition,
      flyTo,
      setAILayerOpacity,
      startGlobalRotation,
      stopGlobalRotation,
      setGlobeVisible,
      applyAct2StoryboardPresetA,
      setInspectionBeacon,
      clearInspectionBeacon,
      loadInsarPoints,
      clearInsarPoints,
      loadHeritageBuildings,
      clearHeritageBuildings,
      loadHeritagePointCloud,
      clearHeritagePointCloud,
      setCinematicMode,
      loadWindScene,
      clearWindScene,
      performDive
    }
  }
}
</script>

<style scoped>
.cesium-viewer-container {
  position: relative;
  width: 100%;
  height: 100%;
}

#cesiumContainer {
  width: 100%;
  height: 100%;
  /* Let Cesium handle gestures inside the canvas container.
     HUD overlays can opt into vertical scrolling with touch-action: pan-y. */
  touch-action: none;
  overscroll-behavior: none;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 5px solid rgba(0, 245, 255, 0.2);
  border-top-color: #00F5FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 20px;
  color: #00F5FF;
  font-size: 16px;
  font-weight: 500;
}

.credit-container {
  position: absolute;
  left: 10px;
  bottom: 10px;
  z-index: 1000;
  max-width: min(520px, calc(100vw - 20px));
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(10, 15, 25, 0.55);
  backdrop-filter: blur(6px);
}

/* PoC demo: hide upgrade/attribution credit text completely. */
.credit-container {
  display: none !important;
}

/* Some Cesium builds render the credit lightbox outside the container. */
:deep(.cesium-credit-lightbox),
:deep(.cesium-credit-lightbox-overlay) {
  display: none !important;
}

.credit-container :deep(.cesium-widget-credits) {
  position: static;
  display: block;
  margin: 0;
  padding: 0;
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
  text-shadow: none;
}

/* Demo polish: hide Ion logo only (keep credit text unless removed elsewhere). */
.credit-container :deep(.cesium-credit-logoContainer),
.credit-container :deep(.cesium-credit-logo),
.credit-container :deep(a.cesium-credit-logo) {
  display: none !important;
}

</style>
