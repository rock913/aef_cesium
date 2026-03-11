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
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

export default {
  name: 'CesiumViewer',
  props: {
    initialLocation: {
      type: Object,
      default: () => ({ lat: 39.0500, lon: 115.9800, height: 15000 })
    }
  },
  emits: ['viewer-ready', 'camera-moved', 'map-center-changed', 'imagery-error', 'tile-load-progress'],
  
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
      if (viewer) {
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
        viewer.destroy()
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
      
      // 添加新图层
      const provider = new Cesium.UrlTemplateImageryProvider({
        url: tileUrl,
        tileWidth: 256,
        tileHeight: 256,
        minimumLevel: 0,
        // 透明 PNG 也应被视为“成功瓦片”，否则 Cesium 可能持续丢弃并重试
        tileDiscardPolicy: new Cesium.NeverTileDiscardPolicy(),
        maximumLevel: 18
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
      applyAct2StoryboardPresetA
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
