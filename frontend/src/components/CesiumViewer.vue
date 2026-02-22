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
    let tileLoadUnsub = null
    let ionBaseProviderUnsub = null
    let rotationTick = null
    let fadeTimer = null
    let centerTick = null
    let centerRafPending = false
    let lastCenterLat = null
    let lastCenterLon = null
    
    onMounted(() => {
      initViewer()
    })
    
    onBeforeUnmount(() => {
      if (viewer) {
        if (tileLoadUnsub) tileLoadUnsub()
        if (currentAIProviderUnsub) currentAIProviderUnsub()
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
    
    function initViewer() {
      const ionToken = import.meta.env.VITE_CESIUM_TOKEN
      const hasIonToken = !!(ionToken && String(ionToken).trim())
      if (hasIonToken) {
        Cesium.Ion.defaultAccessToken = ionToken
      }
      
      try {
        // Basemap strategy:
        // - If Ion token exists, do NOT override imageryProvider/baseLayer so Cesium loads its stable default imagery.
        //   This fixes the "blue grid" and many third-party basemap failures.
        // - If no token, fall back to a grid so the globe is still visible.
        const fallbackImageryProvider = new Cesium.GridImageryProvider()

        viewer = new Cesium.Viewer(cesiumContainer.value, {
          creditContainer: creditContainer.value,
          terrain: hasIonToken
            ? Cesium.Terrain.fromWorldTerrain({
                requestWaterMask: true,
                requestVertexNormals: true
              })
            : new Cesium.EllipsoidTerrainProvider(),

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
        
        // Optional 3D buildings (requires network; works best with Ion token)
        try {
          if (hasIonToken) {
            viewer.scene.primitives.add(Cesium.createOsmBuildings())
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

      const baseLayer = viewer.imageryLayers.get(0)
      const splitPos = Math.min(0.98, Math.max(0.02, Number(position) || 0.5))

      if (enabled) {
        viewer.scene.splitPosition = splitPos
        if (baseLayer) baseLayer.splitDirection = Cesium.SplitDirection.LEFT
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
