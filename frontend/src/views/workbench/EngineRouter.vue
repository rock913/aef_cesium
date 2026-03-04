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

const initialLocation = computed(() => props.scenario?.camera || undefined)

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
  emit('viewer-ready', viewer)
  try {
    void applyLayersAsync(props.layers)
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
  map.delete(id)
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

async function applyLayersAsync(layers) {
  const viewer = cesiumViewerInstance.value
  if (!viewer) return

  const token = (applyToken.value += 1)
  const arr = Array.isArray(layers) ? layers : []

  // 1) Boundaries (GeoJSON)
  try {
    const l = arr.find((x) => String(x?.id || '') === 'boundaries')
    const enabled = !!l?.enabled
    const opacity = _getLayerParam(l, 'opacity', 0.9)
    await _ensureGeoJsonBoundaries({ enabled, opacity, token })
  } catch (_) {
    // ignore
  }

  // 2) Imagery overlays (GEE tiles via backend proxy)
  for (const l of arr) {
    const id = String(l?.id || '').trim()
    if (!id || id === 'boundaries') continue
    const enabled = !!l?.enabled
    const opacity = _getLayerParam(l, 'opacity', 0.8)

    const opts = {}
    if (id === 'anomaly-mask') {
      opts.variant = 'anomaly-mask'
      const thr = Number(_getLayerParam(l, 'threshold', 0.1))
      if (Number.isFinite(thr)) opts.threshold = thr
      const pal = String(_getLayerParam(l, 'palette', '') || '').trim()
      if (pal) opts.palette = pal
    } else {
      opts.variant = 'heatmap'
    }

    await _ensureImageryLayerForId({ id, enabled, opacity, options: opts, token })
  }

  if (token !== applyToken.value) return
  _reorderImageryLayers(arr)

  try {
    viewer.scene?.requestRender?.()
  } catch (_) {
    // ignore
  }
}

watch(
  () => props.scenario?.id,
  () => {
    flyToScenario()
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
  applyLayers: applyLayersAsync,
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
