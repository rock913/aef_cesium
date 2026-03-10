<template>
  <div class="engine-router" aria-label="Engine Router">
    <!-- MVP: always mount Cesium Twin. Three.js modes are Phase 2. -->
    <CesiumViewer
      ref="cesiumViewer"
      :initial-location="initialLocation"
      @viewer-ready="onViewerReady"
    />
  </div>
</template>

<script setup>
import * as Cesium from 'cesium'
import { computed, ref, watch } from 'vue'
import CesiumViewer from '../../components/CesiumViewer.vue'
import { apiService } from '../../services/api.js'

const props = defineProps({
  scenario: { type: Object, default: null },
  layers: { type: Array, default: () => [] },
})

const emit = defineEmits(['viewer-ready'])

const cesiumViewer = ref(null)
const cesiumViewerInstance = ref(null)
const overlayHandles = ref(new Map())
const applyToken = ref(0)

const swipeEnabled = ref(false)
const swipePosition = ref(0.5)

let _vectorSwipeUnsub = null

function _disableDefaultDoubleClick(viewer) {
  if (!viewer) return
  try {
    const h = viewer?.cesiumWidget?.screenSpaceEventHandler || viewer?.screenSpaceEventHandler
    h?.removeInputAction?.(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
  } catch (_) {
    // ignore
  }
}

function _entityRepresentativeCartesian(ent, time) {
  if (!ent) return null
  try {
    if (ent.position) {
      const p = ent.position.getValue?.(time) ?? ent.position
      if (p) return p
    }
  } catch (_) {
    // ignore
  }

  // Polygon centroid-ish: bounding sphere center of hierarchy positions.
  try {
    const h = ent?.polygon?.hierarchy
    if (h && typeof h.getValue === 'function') {
      const v = h.getValue(time)
      const pts = Array.isArray(v?.positions) ? v.positions : null
      if (pts && pts.length) {
        const bs = Cesium.BoundingSphere.fromPoints(pts)
        if (bs?.center) return bs.center
      }
    }
  } catch (_) {
    // ignore
  }

  // Polyline centroid-ish.
  try {
    const posProp = ent?.polyline?.positions
    if (posProp && typeof posProp.getValue === 'function') {
      const pts = posProp.getValue(time)
      if (Array.isArray(pts) && pts.length) {
        const bs = Cesium.BoundingSphere.fromPoints(pts)
        if (bs?.center) return bs.center
      }
    }
  } catch (_) {
    // ignore
  }

  return null
}

function _sceneCartesianToWindow(scene, cartesian, result) {
  if (!scene || !cartesian) return null
  const st = Cesium.SceneTransforms
  const fn = (st && (st.worldToWindowCoordinates || st.wgs84ToWindowCoordinates)) || null
  if (typeof fn !== 'function') return null
  try {
    return fn(scene, cartesian, result)
  } catch (_) {
    return null
  }
}

function _stopVectorSwipeHook(viewer) {
  try {
    if (_vectorSwipeUnsub) {
      _vectorSwipeUnsub()
      _vectorSwipeUnsub = null
    }
  } catch (_) {
    _vectorSwipeUnsub = null
  }

  // Restore entity.show so ds.show remains the single source of truth.
  try {
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'geojson' || !entry.dataSource) continue
      for (const ent of entry.dataSource.entities.values) ent.show = true
    }
  } catch (_) {
    // ignore
  }

  try {
    viewer?.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
}

function _ensureVectorSwipeHook(viewer) {
  if (!viewer) return
  if (_vectorSwipeUnsub) return

  const scene = viewer.scene
  if (!scene) return

  // Fallback for Entity/DataSource overlays: approximate a vertical "cut" by
  // hiding entities based on their screen-space centroid relative to splitPosition.
  const scratchWin = new Cesium.Cartesian2()
  const cb = () => {
    const enabled = !!swipeEnabled.value
    if (!enabled) return

    const t = viewer.clock?.currentTime || Cesium.JulianDate.now()
    const pos = Math.max(0, Math.min(1, Number(swipePosition.value) || 0.5))
    const canvas = scene.canvas
    const w = Number(canvas?.clientWidth || canvas?.width || 0)
    if (!w) return
    const splitX = pos * w

    // Patch 0303: left stays as clean basemap; all GeoJSON overlays are treated
    // as RIGHT-side overlays (hide anything left of split).
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'geojson' || !entry.dataSource) continue
      if (!entry.dataSource.show) continue
      for (const ent of entry.dataSource.entities.values) {
        const c = _entityRepresentativeCartesian(ent, t)
        if (!c) continue
        const win = _sceneCartesianToWindow(scene, c, scratchWin)
        if (!win) continue
        const x = Number(win.x)
        if (!Number.isFinite(x)) continue
        ent.show = x >= splitX
      }
    }
  }

  try {
    scene.preRender.addEventListener(cb)
    _vectorSwipeUnsub = () => {
      try {
        scene.preRender.removeEventListener(cb)
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    _vectorSwipeUnsub = null
  }
}

function _applyVectorSwipeState(viewer, enabled) {
  if (!viewer) return
  if (!enabled) {
    _stopVectorSwipeHook(viewer)
    return
  }
  _ensureVectorSwipeHook(viewer)
}

function _viewerAlive() {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return null
  try {
    if (typeof viewer.isDestroyed === 'function' && viewer.isDestroyed()) return null
  } catch (_) {
    // ignore
  }
  return viewer
}

const _RUNTIME_KEYS = Object.freeze({
  tileset: 'phase3-tileset',
  czml: 'phase3-czml',
  extruded: 'phase3-extruded',
})

// Global Standby default: start from a deep-space view.
// Local context dives are triggered by explicit tool calls (e.g., camera_fly_to / fly_to).
const initialLocation = computed(() => ({ lon: 105.0, lat: 35.0, height: 20000000.0 }))

function flyToScenario() {
  const cam = props.scenario?.camera
  if (!cam) return
  try {
    const d = Number(cam.duration_s)
    const duration = Number.isFinite(d) && d > 0 ? d : 3.8
    cesiumViewer.value?.flyTo?.(cam, duration)
  } catch (_) {
    // ignore
  }
}

function onViewerReady(viewer) {
  cesiumViewerInstance.value = viewer || null
  _disableDefaultDoubleClick(viewer)
  emit('viewer-ready', viewer)
  try {
    void applyLayersAsync(props.layers)
  } catch (_) {
    // ignore
  }
}

function startGlobalStandby() {
  try {
    cesiumViewer.value?.startGlobalRotation?.()
  } catch (_) {
    // ignore
  }
}

function stopGlobalStandby() {
  try {
    cesiumViewer.value?.stopGlobalRotation?.()
  } catch (_) {
    // ignore
  }
}

function flyToLocation(location, duration = 3.8) {
  try {
    cesiumViewer.value?.flyTo?.(location, duration)
  } catch (_) {
    // ignore
  }
}

function _scenarioBackend() {
  const b = props.scenario?.backend || {}
  return {
    mode: String(b.mode || '').trim(),
    location: String(b.location || '').trim(),
  }
}

function _getLayerParam(l, key, fallback) {
  try {
    const v = l?.params?.[key]
    return v === undefined ? fallback : v
  } catch (_) {
    return fallback
  }
}

function _clamp01(x, fallback = 1) {
  const n = Number(x)
  if (!Number.isFinite(n)) return fallback
  return Math.max(0, Math.min(1, n))
}

function _overlayEntry(id) {
  const map = overlayHandles.value
  return map.get(id) || null
}

function _setOverlayEntry(id, entry) {
  overlayHandles.value.set(id, entry)
}

function _removeOverlayEntry(id) {
  const map = overlayHandles.value
  const entry = map.get(id)
  if (!entry) return
  const viewer = cesiumViewerInstance.value
  try {
    if (entry.kind === 'imagery' && entry.layer && viewer) {
      viewer.imageryLayers.remove(entry.layer, true)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'geojson' && entry.dataSource && viewer) {
      viewer.dataSources.remove(entry.dataSource, true)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'tileset' && entry.tileset && viewer) {
      viewer.scene?.primitives?.remove?.(entry.tileset)
    }
  } catch (_) {
    // ignore
  }
  try {
    if (entry.kind === 'czml' && entry.dataSource && viewer) {
      viewer.dataSources.remove(entry.dataSource, true)
    }
  } catch (_) {
    // ignore
  }
  map.delete(id)
}

async function enable3DTerrain(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const terrainKey = String(options?.terrain || 'cesium_world_terrain').trim().toLowerCase()
  if (!terrainKey) return false

  try {
    if (terrainKey === 'cesium_world_terrain') {
      if (typeof Cesium.createWorldTerrainAsync === 'function') {
        viewer.terrainProvider = await Cesium.createWorldTerrainAsync()
      } else if (typeof Cesium.createWorldTerrain === 'function') {
        viewer.terrainProvider = Cesium.createWorldTerrain()
      }
      try {
        if (viewer.scene?.globe) viewer.scene.globe.depthTestAgainstTerrain = true
      } catch (_) {
        // ignore
      }
      return true
    }
  } catch (_) {
    // ignore
  }

  return false
}

async function addCesium3DTiles(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const url = String(options?.url || '').trim()
  const ionAssetIdRaw = options?.ion_asset_id
  const ionAssetId = Number(ionAssetIdRaw)

  _removeOverlayEntry(_RUNTIME_KEYS.tileset)

  let resourceUrl = url
  try {
    if (!resourceUrl && Number.isFinite(ionAssetId) && ionAssetId > 0 && Cesium?.IonResource?.fromAssetId) {
      resourceUrl = await Cesium.IonResource.fromAssetId(ionAssetId)
    }
  } catch (_) {
    // ignore
  }

  if (!resourceUrl) return false

  try {
    const tileset = await Cesium.Cesium3DTileset.fromUrl(resourceUrl)
    viewer.scene.primitives.add(tileset)
    _setOverlayEntry(_RUNTIME_KEYS.tileset, { kind: 'tileset', tileset })
    return true
  } catch (_) {
    return false
  }
}

function setSceneMode(mode = 'day') {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const m = String(mode || '').trim().toLowerCase()
  const isNight = m === 'night'

  try {
    if (viewer.scene?.globe) viewer.scene.globe.enableLighting = isNight
  } catch (_) {
    // ignore
  }

  try {
    if (isNight) {
      const d = new Date('2026-03-03T16:00:00Z')
      viewer.clock.currentTime = Cesium.JulianDate.fromDate(d)
      viewer.clock.shouldAnimate = false
    }
  } catch (_) {
    // ignore
  }

  return true
}

async function playCzmlAnimation(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const czmlUrl = String(options?.czml_url || '').trim()
  const czml = Array.isArray(options?.czml) ? options.czml : null
  const speed = Number(options?.speed)

  _removeOverlayEntry(_RUNTIME_KEYS.czml)

  try {
    const ds = czmlUrl
      ? await Cesium.CzmlDataSource.load(czmlUrl)
      : await Cesium.CzmlDataSource.load(czml || [])

    viewer.dataSources.add(ds)
    _setOverlayEntry(_RUNTIME_KEYS.czml, { kind: 'czml', dataSource: ds })

    try {
      viewer.clock.multiplier = Number.isFinite(speed) && speed > 0 ? speed : 1.0
      viewer.clock.shouldAnimate = true
    } catch (_) {
      // ignore
    }

    return true
  } catch (_) {
    return false
  }
}

function setGlobeTransparency(alpha = 1.0) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const a = Number(alpha)
  if (!Number.isFinite(a)) return false
  const clamped = Math.max(0, Math.min(1, a))

  try {
    const globe = viewer.scene?.globe
    if (!globe) return false
    globe.translucency.enabled = clamped < 0.999
    globe.translucency.frontFaceAlpha = clamped
    globe.translucency.backFaceAlpha = clamped
    return true
  } catch (_) {
    return false
  }
}

async function addExtrudedPolygons(options = {}) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return false

  const geojson = options?.geojson
  if (!geojson) return false

  const height = Number(options?.height)
  const opacity = Number(options?.opacity)
  const css = String(options?.color || '#00F0FF').trim() || '#00F0FF'
  const a = Number.isFinite(opacity) ? Math.max(0.05, Math.min(1, opacity)) : 0.55
  const fill = Cesium.Color.fromCssColorString(css).withAlpha(a)
  const stroke = fill.withAlpha(Math.min(0.9, a + 0.25))
  const baseFill = fill.withAlpha(Math.max(0.12, a * 0.25))

  _removeOverlayEntry(_RUNTIME_KEYS.extruded)

  try {
    const ds = await Cesium.GeoJsonDataSource.load(geojson, {
      clampToGround: true,
      // IMPORTANT: disable GeoJSON default stroke at load-time.
      // Otherwise Cesium may create terrain-clamped polygon outlines and emit
      // the one-time warning before we can set `polygon.outline = false`.
      stroke: Cesium.Color.TRANSPARENT,
      strokeWidth: 0,
      fill: baseFill,
    })

    for (const ent of ds.entities.values) {
      const poly = ent?.polygon
      if (!poly) continue
      try {
        if (Number.isFinite(height)) poly.extrudedHeight = height
      } catch (_) {
        // ignore
      }
      try {
        poly.outline = false
        poly.material = fill
      } catch (_) {
        // ignore
      }

      // If the GeoJSON contains line features, re-apply a visible stroke.
      const line = ent?.polyline
      if (line) {
        try {
          line.clampToGround = true
          line.width = 2
          line.material = stroke
        } catch (_) {
          // ignore
        }
      }
    }

    viewer.dataSources.add(ds)
    _setOverlayEntry(_RUNTIME_KEYS.extruded, { kind: 'geojson', dataSource: ds, sig: `extruded:${Date.now()}` })
    return true
  } catch (_) {
    return false
  }
}

async function _ensureAiVector({ enabled, opacity, geojson, token, color }) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const id = 'ai-vector'
  const sig = `ai-vector:${JSON.stringify(geojson || null)}:${String(color || '')}`
  const existing = _overlayEntry(id)

  if (existing?.kind === 'geojson' && existing.sig === sig) {
    try {
      existing.dataSource.show = !!enabled
    } catch (_) {
      // ignore
    }
    // opacity update is best-effort (some entity materials may not exist).
    try {
      const a = _clamp01(opacity, 0.9)
      const css = String(color || '#00F0FF').trim() || '#00F0FF'
      const c = Cesium.Color.fromCssColorString(css).withAlpha(Math.max(0.15, a))
      for (const ent of existing.dataSource.entities.values) {
        if (ent?.polyline?.material) ent.polyline.material = c
        if (ent?.polygon) {
          if (ent.polygon.material) ent.polygon.material = c.withAlpha(Math.max(0.10, a * 0.35))
          ent.polygon.outline = false
        }
        if (ent?.point?.color) ent.point.color = c
      }
    } catch (_) {
      // ignore
    }
    return
  }

  _removeOverlayEntry(id)
  if (!geojson) return

  try {
    const a = _clamp01(opacity, 0.9)
    const css = String(color || '#00F0FF').trim() || '#00F0FF'
    const stroke = Cesium.Color.fromCssColorString(css).withAlpha(Math.max(0.15, a))
    const fill = stroke.withAlpha(Math.max(0.10, a * 0.35))

    const ds = await Cesium.GeoJsonDataSource.load(geojson, {
      clampToGround: true,
      // IMPORTANT: disable GeoJSON default stroke at load-time.
      // Otherwise Cesium may create terrain-clamped polygon outlines and emit
      // the one-time warning before we can set `polygon.outline = false`.
      stroke: Cesium.Color.TRANSPARENT,
      strokeWidth: 0,
      fill,
    })
    if (token !== applyToken.value) return

    // Re-apply styling post-load so polylines remain visible while polygon
    // outlines stay disabled on terrain.
    try {
      for (const ent of ds.entities.values) {
        if (ent?.polyline) {
          try {
            ent.polyline.clampToGround = true
            ent.polyline.width = 2
            ent.polyline.material = stroke
          } catch (_) {
            // ignore
          }
        }
        if (ent?.polygon) {
          try {
            ent.polygon.outline = false
            ent.polygon.material = fill
          } catch (_) {
            // ignore
          }
        }
        if (ent?.point) {
          try {
            ent.point.color = stroke
          } catch (_) {
            // ignore
          }
        }
      }
    } catch (_) {
      // ignore
    }
    try {
      ds.show = !!enabled
    } catch (_) {
      // ignore
    }
    viewer.dataSources.add(ds)
    _setOverlayEntry(id, { kind: 'geojson', dataSource: ds, sig })
  } catch (_) {
    // ignore
  }
}

async function _ensureGeoJsonBoundaries({ enabled, opacity, token }) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const { mode, location } = _scenarioBackend()
  if (!location) return

  const id = 'boundaries'
  const sig = `geojson:${location}:${mode}`

  const existing = _overlayEntry(id)
  if (existing?.kind === 'geojson' && existing.sig === sig) {
    try {
      existing.dataSource.show = !!enabled
    } catch (_) {
      // ignore
    }
    try {
      const a = _clamp01(opacity, 0.9)
      const outlineAlpha = Math.max(0.15, a)

      // IMPORTANT:
      // Cesium warns that polygon outlines are unsupported when clamped to terrain.
      // We keep polygon fill transparent, disable polygon outlines, and draw a
      // separate clamped polyline as the visible boundary.
      const t = Cesium.JulianDate.now()
      for (const ent of existing.dataSource.entities.values) {
        const poly = ent?.polygon
        if (poly) {
          poly.material = Cesium.Color.TRANSPARENT
          poly.outline = false

          // Ensure we have a matching outline polyline.
          try {
            const props = ent?.properties
            const hasLine = !!(props && (props.__oneearth_has_outline?.getValue?.() ?? props.__oneearth_has_outline))
            if (!hasLine && poly?.hierarchy) {
              const h = poly.hierarchy.getValue(t)
              const positions = Array.isArray(h?.positions) ? h.positions : null
              if (positions && positions.length >= 3) {
                const closed = positions[0] === positions[positions.length - 1]
                const linePositions = closed ? positions : [...positions, positions[0]]
                existing.dataSource.entities.add({
                  name: `${ent?.name || 'Boundary'} (outline)`,
                  polyline: {
                    positions: linePositions,
                    clampToGround: true,
                    width: 2,
                    material: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(outlineAlpha),
                  },
                  properties: {
                    __oneearth_outline: true,
                    __oneearth_for: String(ent?.id || ''),
                  },
                })

                try {
                  if (props && typeof props.addProperty === 'function') {
                    props.addProperty('__oneearth_has_outline')
                    props.__oneearth_has_outline = true
                  } else if (props) {
                    props.__oneearth_has_outline = true
                  }
                } catch (_) {
                  // ignore
                }
              }
            }
          } catch (_) {
            // ignore
          }
        }

        // Update any existing outline polylines.
        const line = ent?.polyline
        if (line && line.material) {
          try {
            const isOutline = !!(ent?.properties && (ent.properties.__oneearth_outline?.getValue?.() ?? ent.properties.__oneearth_outline))
            if (isOutline) {
              line.material = Cesium.Color.fromCssColorString('#00F0FF').withAlpha(outlineAlpha)
            }
          } catch (_) {
            // ignore
          }
        }
      }
    } catch (_) {
      // ignore
    }
    return
  }

  // Replace any existing stub/old DS.
  _removeOverlayEntry(id)

  const url = `/api/geojson/boundaries?location=${encodeURIComponent(location)}${mode ? `&mode=${encodeURIComponent(mode)}` : ''}`

  try {
    const ds = await Cesium.GeoJsonDataSource.load(url, {
      clampToGround: true,
      // IMPORTANT: disable GeoJSON default stroke at load-time.
      // Otherwise Cesium will create terrain-clamped polygon outlines and emit
      // the one-time warning before we can set `polygon.outline = false`.
      stroke: Cesium.Color.TRANSPARENT,
      strokeWidth: 0,
      fill: Cesium.Color.TRANSPARENT,
    })
    if (token !== applyToken.value) return

    const a = _clamp01(opacity, 0.9)
    const outlineAlpha = Math.max(0.15, a)
    const t = Cesium.JulianDate.now()

    try {
      for (const ent of ds.entities.values) {
        const poly = ent?.polygon
        if (poly) {
          // Keep fill transparent. Disable polygon outlines to avoid the Cesium warning.
          poly.material = Cesium.Color.TRANSPARENT
          poly.outline = false

          // Derive a boundary polyline from the polygon hierarchy.
          try {
            const h = poly?.hierarchy?.getValue?.(t)
            const positions = Array.isArray(h?.positions) ? h.positions : null
            if (positions && positions.length >= 3) {
              const closed = positions[0] === positions[positions.length - 1]
              const linePositions = closed ? positions : [...positions, positions[0]]
              ds.entities.add({
                name: `${ent?.name || 'Boundary'} (outline)`,
                polyline: {
                  positions: linePositions,
                  clampToGround: true,
                  width: 2,
                  material: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(outlineAlpha),
                },
                properties: {
                  __oneearth_outline: true,
                  __oneearth_for: String(ent?.id || ''),
                },
              })

              // Compute a centroid-ish label position.
              try {
                let sumLat = 0
                let sumLon = 0
                let n = 0
                for (const p of positions) {
                  const c = Cesium.Cartographic.fromCartesian(p)
                  sumLat += c.latitude
                  sumLon += c.longitude
                  n += 1
                }
                if (n > 0) {
                  const lat = sumLat / n
                  const lon = sumLon / n
                  ent.position = Cesium.Cartesian3.fromRadians(lon, lat, 0)
                }
              } catch (_) {
                // ignore
              }
            }
          } catch (_) {
            // ignore
          }

          // Mark so the update-path can avoid duplicating lines.
          try {
            const props = ent?.properties
            if (props && typeof props.addProperty === 'function') {
              props.addProperty('__oneearth_has_outline')
              props.__oneearth_has_outline = true
            } else if (props) {
              props.__oneearth_has_outline = true
            }
          } catch (_) {
            // ignore
          }
        }

        // Optional label.
        try {
          const name = String(ent?.properties?.name?.getValue?.() || ent?.properties?.name || '').trim()
          if (name) {
            ent.label = new Cesium.LabelGraphics({
              text: name,
              font: '12px sans-serif',
              fillColor: Cesium.Color.fromCssColorString('#00F0FF').withAlpha(0.85),
              outlineColor: Cesium.Color.BLACK.withAlpha(0.55),
              outlineWidth: 2,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              pixelOffset: new Cesium.Cartesian2(0, -14),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            })
          }
        } catch (_) {
          // ignore
        }
      }
    } catch (_) {
      // ignore
    }

    ds.show = !!enabled
    viewer.dataSources.add(ds)
    _setOverlayEntry(id, { kind: 'geojson', dataSource: ds, sig })
  } catch (_) {
    // Best-effort only
  }
}

async function _ensureImageryLayerForId({ id, enabled, opacity, options, token }) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return
  if (!id) return

  const { mode, location } = _scenarioBackend()
  if (!mode || !location) return

  if (!enabled) {
    const e = _overlayEntry(id)
    if (e?.kind === 'imagery' && e.layer) {
      try {
        e.layer.show = false
      } catch (_) {
        // ignore
      }
    }
    return
  }

  const opts = options && typeof options === 'object' ? options : {}
  // AI imagery overlay: allow a direct tile template URL from tool-calling events.
  if (id === 'ai-imagery') {
    const direct = String((opts && (opts.tile_url || opts.url)) || '').trim()
    const sig = `ai-imagery:${direct}:${JSON.stringify(opts)}`
    const existing = _overlayEntry(id)

    if (existing?.kind === 'imagery' && existing.sig === sig) {
      try {
        existing.layer.show = true
        existing.layer.alpha = _clamp01(opacity, 0.65)
      } catch (_) {
        // ignore
      }
      return
    }

    _removeOverlayEntry(id)
    if (!direct) return
    if (token !== applyToken.value) return

    try {
      const provider = new Cesium.UrlTemplateImageryProvider({
        url: direct,
        tilingScheme: new Cesium.WebMercatorTilingScheme(),
        maximumLevel: 24,
        enablePickFeatures: false,
      })
      const layer = viewer.imageryLayers.addImageryProvider(provider)
      try {
        layer.__oneearthOverlay = true
      } catch (_) {
        // ignore
      }
      layer.alpha = _clamp01(opacity, 0.65)
      layer.show = !!enabled
      _setOverlayEntry(id, { kind: 'imagery', layer, sig })
    } catch (_) {
      // ignore
    }
    return
  }

  const sig = `${id}:${mode}:${location}:${JSON.stringify(opts)}`
  const existing = _overlayEntry(id)

  if (existing?.kind === 'imagery' && existing.sig === sig) {
    try {
      existing.layer.show = true
      existing.layer.alpha = _clamp01(opacity, 0.8)
    } catch (_) {
      // ignore
    }
    return
  }

  // Fetch tile URL from backend (same-origin /api/tiles proxy).
  let tileUrl = ''
  try {
    const resp = await apiService.getLayer(mode, location, opts)
    tileUrl = String(resp?.tile_url || '').trim()
  } catch (_) {
    tileUrl = ''
  }
  if (!tileUrl) return
  if (token !== applyToken.value) return

  // Replace existing layer if sig changed.
  _removeOverlayEntry(id)

  try {
    const provider = new Cesium.UrlTemplateImageryProvider({
      url: tileUrl,
      tilingScheme: new Cesium.WebMercatorTilingScheme(),
      // Allow deeper zoom when the camera is close to ground.
      maximumLevel: 24,
      enablePickFeatures: false,
    })

    const layer = viewer.imageryLayers.addImageryProvider(provider)
    // Mark as an externally-managed overlay (used by CesiumViewer to avoid
    // photorealistic 3D tileset occluding Workbench imagery overlays).
    try {
      layer.__oneearthOverlay = true
    } catch (_) {
      // ignore
    }
    layer.alpha = _clamp01(opacity, 0.8)
    layer.show = !!enabled
    _setOverlayEntry(id, { kind: 'imagery', layer, sig })
  } catch (_) {
    // ignore
  }
}

function _reorderImageryLayers(layers) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return
  const arr = Array.isArray(layers) ? layers : []
  const imageryIds = arr
    .map((l) => String(l?.id || '').trim())
    .filter((id) => id && id !== 'boundaries')
    .filter((id) => {
      const e = _overlayEntry(id)
      return e?.kind === 'imagery' && !!e?.layer
    })

  // Treat LayerTree list order as TOP -> BOTTOM.
  // Raise from bottom to top so the first item ends on top.
  for (const id of imageryIds.slice().reverse()) {
    const e = _overlayEntry(id)
    if (e?.kind !== 'imagery' || !e.layer) continue
    try {
      viewer.imageryLayers.raiseToTop(e.layer)
    } catch (_) {
      // ignore
    }
  }
}

function _resetSwipeDirections(viewer) {
  if (!viewer) return
  const SD = Cesium.SplitDirection || Cesium.ImagerySplitDirection
  if (!SD) return
  try {
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'imagery' || !entry?.layer) continue
      try {
        entry.layer.splitDirection = SD.NONE
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }
}

function _applySwipeState(viewer) {
  if (!viewer) return
  const enabled = !!swipeEnabled.value
  const pos = Math.max(0, Math.min(1, Number(swipePosition.value) || 0.5))

  try {
    viewer.scene.splitPosition = enabled ? pos : 0.5
  } catch (_) {
    // ignore
  }

  _resetSwipeDirections(viewer)

  // Apply vector swipe behavior (fallback for Entity/DataSource overlays).
  try {
    _applyVectorSwipeState(viewer, enabled)
  } catch (_) {
    // ignore
  }

  if (!enabled) return

  // Patch 0303: left stays clean basemap; force all overlay imagery layers to RIGHT.
  const SD = Cesium.SplitDirection || Cesium.ImagerySplitDirection
  if (!SD) return
  try {
    for (const [, entry] of overlayHandles.value.entries()) {
      if (entry?.kind !== 'imagery' || !entry?.layer) continue
      try {
        if (entry.layer.show !== false) entry.layer.splitDirection = SD.RIGHT
      } catch (_) {
        // ignore
      }
    }
  } catch (_) {
    // ignore
  }
}

function setSwipeMode(opts = {}) {
  swipeEnabled.value = !!opts?.enabled
  const pos = Number(opts?.position)
  if (Number.isFinite(pos)) swipePosition.value = Math.max(0, Math.min(1, pos))

  const viewer = _viewerAlive()
  _applySwipeState(viewer)
  try {
    viewer?.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
  return true
}

function setSwipePosition01(pos) {
  const n = Number(pos)
  if (!Number.isFinite(n)) return false
  swipePosition.value = Math.max(0, Math.min(1, n))
  const viewer = _viewerAlive()
  if (viewer && swipeEnabled.value) {
    _applySwipeState(viewer)
    try {
      viewer.scene?.requestRender?.()
    } catch (_) {
      // ignore
    }
  }
  return true
}

async function applyLayersAsync(layers) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const token = (applyToken.value += 1)
  const arr = Array.isArray(layers) ? layers : []

  const loadTasks = []

  // 1) Boundaries (GeoJSON)
  try {
    const l = arr.find((x) => String(x?.id || '') === 'boundaries')
    if (l) {
      const enabled = !!l?.enabled
      const opacity = _getLayerParam(l, 'opacity', 0.9)
      loadTasks.push(_ensureGeoJsonBoundaries({ enabled, opacity, token }))
    }
  } catch (_) {
    // ignore
  }

  // 2) AI vector overlay (GeoJSON)
  try {
    const l = arr.find((x) => String(x?.id || '') === 'ai-vector')
    if (l) {
      const enabled = !!l?.enabled
      const opacity = _getLayerParam(l, 'opacity', 0.9)
      const geojson = _getLayerParam(l, 'geojson', null)
      const color = String(_getLayerParam(l, 'color', '#00F0FF') || '').trim() || '#00F0FF'
      loadTasks.push(_ensureAiVector({ enabled, opacity, geojson, token, color }))
    }
  } catch (_) {
    // ignore
  }

  // 3) Imagery overlays (GEE tiles via backend proxy, plus ai-imagery direct URL)
  for (const l of arr) {
    const id = String(l?.id || '').trim()
    if (!id || id === 'boundaries') continue
    if (id === 'ai-vector') continue
    const enabled = !!l?.enabled
    const opacity = _getLayerParam(l, 'opacity', 0.8)

    const opts = {}
    if (id === 'ai-imagery') {
      const tileUrl = String(_getLayerParam(l, 'tile_url', '') || '').trim()
      if (tileUrl) opts.tile_url = tileUrl
    }
    if (id === 'anomaly-mask') {
      opts.variant = 'anomaly-mask'
      const thr = Number(_getLayerParam(l, 'threshold', 0.1))
      if (Number.isFinite(thr)) opts.threshold = thr
      const pal = String(_getLayerParam(l, 'palette', '') || '').trim()
      if (pal) opts.palette = pal
    } else {
      opts.variant = 'heatmap'
    }

    try {
      loadTasks.push(_ensureImageryLayerForId({ id, enabled, opacity, options: opts, token }))
    } catch (_) {
      // ignore
    }
  }

  try {
    await Promise.allSettled(loadTasks)
  } catch (_) {
    // ignore
  }

  if (token !== applyToken.value) return
  _reorderImageryLayers(arr)

  try {
    _applySwipeState(viewer)
  } catch (_) {
    // ignore
  }

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
}

watch(
  () => props.scenario?.id,
  () => {
    try {
      void applyLayersAsync(props.layers)
    } catch (_) {
      // ignore
    }
  }
)

watch(
  () => props.layers,
  (v) => {
    try {
      void applyLayersAsync(v)
    } catch (_) {
      // ignore
    }
  },
  { deep: true }
)

defineExpose({
  flyToScenario,
  flyToLocation,
  startGlobalStandby,
  stopGlobalStandby,
  applyLayers: applyLayersAsync,
  enable3DTerrain,
  addCesium3DTiles,
  setSceneMode,
  playCzmlAnimation,
  setGlobeTransparency,
  addExtrudedPolygons,
  setSwipeMode,
  setSwipePosition: setSwipePosition01,
  cesiumViewer,
  cesiumViewerInstance,
})
</script>

<style scoped>
.engine-router {
  position: absolute;
  inset: 0;
}

.engine-router :deep(.cesium-viewer-container) {
  width: 100%;
  height: 100%;
}
</style>
