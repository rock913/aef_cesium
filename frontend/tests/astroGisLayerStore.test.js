import { beforeEach, describe, expect, it } from 'vitest'
import {
  __resetAstroStoreForTests,
  ASTRO_GIS_LAYER_IDS,
  useAstroStore,
} from '../src/stores/astroStore.js'

describe('Astro-GIS layer store (Phase 1 foundation)', () => {
  beforeEach(() => {
    __resetAstroStoreForTests()
  })

  it('exposes stable layer ids', () => {
    expect(ASTRO_GIS_LAYER_IDS.MACRO_SDSS).toBe('astro-macro-sdss')
    expect(ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND).toBe('astro-hips-background')
    expect(ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD).toBe('astro-catalog-simbad')
  })

  it('provides default layers with visibility contract', () => {
    const store = useAstroStore()
    const macro = store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.MACRO_SDSS)
    const hips = store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND)
    const simbad = store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD)

    expect(macro?.visible).toBe(true)
    expect(hips?.visible).toBe(false)
    expect(simbad?.visible).toBe(false)
  })

  it('clamps opacity and bumps version', () => {
    const store = useAstroStore()
    const v0 = store.astroGis.value.version

    store.setAstroGisLayerOpacity(ASTRO_GIS_LAYER_IDS.MACRO_SDSS, 2)
    expect(store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.MACRO_SDSS)?.opacity).toBe(1)
    expect(store.astroGis.value.version).toBeGreaterThan(v0)

    store.setAstroGisLayerOpacity(ASTRO_GIS_LAYER_IDS.MACRO_SDSS, -1)
    expect(store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.MACRO_SDSS)?.opacity).toBe(0)
  })

  it('patch merges style/source and supports visibility', () => {
    const store = useAstroStore()
    store.patchAstroGisLayer(ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND, {
      visible: true,
      style: { survey: 'P/allWISE/color' },
      source: { provider: 'aladin-lite-v3' },
    })

    const l = store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.HIPS_BACKGROUND)
    expect(l?.visible).toBe(true)
    expect(l?.style?.survey).toBe('P/allWISE/color')
    expect(l?.source?.provider).toBe('aladin-lite-v3')
  })

  it('reset restores demo layers visible and optional layers hidden', () => {
    const store = useAstroStore()
    store.setAstroGisLayerVisible(ASTRO_GIS_LAYER_IDS.MACRO_SDSS, false)
    store.setAstroGisLayerVisible(ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD, true)
    __resetAstroStoreForTests()

    expect(store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.MACRO_SDSS)?.visible).toBe(true)
    expect(store.getAstroGisLayer(ASTRO_GIS_LAYER_IDS.CATALOG_SIMBAD)?.visible).toBe(false)
  })
})
