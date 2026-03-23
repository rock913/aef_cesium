import { describe, expect, it } from 'vitest'
import { initAladinLiteV3, loadAladinLiteV3 } from '../src/utils/astronomy/aladinLiteAdapter.js'

describe('Aladin Lite adapter (no-dom safe)', () => {
  it('loadAladinLiteV3 returns null in node environment', async () => {
    const A = await loadAladinLiteV3()
    expect(A).toBe(null)
  })

  it('initAladinLiteV3 returns null without DOM/container', async () => {
    const inst = await initAladinLiteV3({ container: null })
    expect(inst).toBe(null)
  })
})
