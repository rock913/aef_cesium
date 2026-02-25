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
import { ref, onMounted, onBeforeUnmount } from 'vue'

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
    
    let viewer = null
    let currentAILayer = null
    let currentAIProviderUnsub = null
    let currentBasemapLayer = null
    let currentBasemapProviderUnsub = null
    let hiddenBaseLayers = []
    let tileLoadUnsub = null
    let ionBaseProviderUnsub = null
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
      if (viewer) {
        if (tileLoadUnsub) tileLoadUnsub()
        if (currentAIProviderUnsub) currentAIProviderUnsub()
        if (currentBasemapProviderUnsub) currentBasemapProviderUnsub()
        if (ionBaseProviderUnsub) ionBaseProviderUnsub()
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
    
    async function initViewer() {
      const ionToken = import.meta.env.VITE_CESIUM_TOKEN
      const hasIonToken = !!(ionToken && String(ionToken).trim())
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
        throw new Error('Cesium container element not found')
      }

      // IMPORTANT: `Viewer` expects a TerrainProvider on `terrainProvider`.
      // Passing a TerrainProvider into `terrain` can crash with:
      //   Cannot read properties of undefined (reading 'addEventListener')
      // because providers like EllipsoidTerrainProvider don't have `readyEvent`.
      let terrainProvider = new Cesium.EllipsoidTerrainProvider()
      if (hasIonToken) {
        try {
          if (typeof Cesium.createWorldTerrainAsync === 'function') {
            terrainProvider = await Cesium.createWorldTerrainAsync({
              requestWaterMask: true,
              requestVertexNormals: true
            })
          } else {
            // Fallback: keep ellipsoid if this build doesn't expose the async helper.
            terrainProvider = new Cesium.EllipsoidTerrainProvider()
          }
        } catch (e) {
          console.warn('⚠️  Failed to load world terrain; falling back to ellipsoid.', e)
          terrainProvider = new Cesium.EllipsoidTerrainProvider()
        }
      }

      try {
        // Basemap strategy:
        // - If Ion token exists, do NOT override imageryProvider/baseLayer so Cesium loads its stable default imagery.
        //   This fixes the "blue grid" and many third-party basemap failures.
        // - If no token, fall back to a grid so the globe is still visible.
        const fallbackImageryProvider = new Cesium.GridImageryProvider()

        viewer = new Cesium.Viewer(cesiumContainer.value, {
          creditContainer: creditContainer.value,
          terrainProvider,

          baseLayerPicker: false,
          ...(hasIonToken
            ? {}
            : { baseLayer: new Cesium.ImageryLayer(fallbackImageryProvider) }),
          
          // UI 控制
          animation: false,
          timeline: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,
          
          // 性能优化
          requestRenderMode: false,
          maximumRenderTimeChange: Infinity
        })

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
        
        // Optional 3D buildings / photorealistic 3D tiles (requires Ion token + network)
        try {
          if (hasIonToken) {
            const photorealisticAssetId = Number(import.meta.env.VITE_ION_PHOTOREALISTIC_ASSET_ID || '')
            const enablePhotorealistic = Number.isFinite(photorealisticAssetId) && photorealisticAssetId > 0

            if (enablePhotorealistic) {
              let tileset = null
              if (Cesium?.Cesium3DTileset?.fromIonAssetId) {
                tileset = await Cesium.Cesium3DTileset.fromIonAssetId(photorealisticAssetId)
              } else {
                const resource = await Cesium.IonResource.fromAssetId(photorealisticAssetId)
                tileset = await Cesium.Cesium3DTileset.fromUrl(resource)
              }
              if (tileset) {
                viewer.scene.primitives.add(tileset)
                try {
                  viewer.scene.globe.depthTestAgainstTerrain = true
                } catch (_) {
                  // ignore
                }
              }
            } else {
              // Lightweight fallback: OSM buildings (not photorealistic, but provides 3D cues)
              viewer.scene.primitives.add(Cesium.createOsmBuildings())
            }
          }
        } catch (_) {
          // ignore
        }

        loading.value = false
        emit('viewer-ready', viewer)

        // Initial center emit.
        try {
          _emitMapCenter()
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
        loadingText.value = '初始化失败: ' + error.message
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
    }

    function setAILayerVisible(visible) {
      if (!viewer) return
      if (currentAILayer) {
        currentAILayer.show = !!visible
      }
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
      stopGlobalRotation
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
