import { beforeEach, describe, expect, it } from 'vitest'
import { __resetResearchStoreForTests, useResearchStore } from '../src/stores/researchStore.js'

describe('useResearchStore (scale state machine)', () => {
  beforeEach(() => {
    __resetResearchStoreForTests()
  })

  it('defaults to earth', () => {
    const store = useResearchStore()
    expect(store.currentScale.value).toBe('earth')
  })

  it('setScale updates the currentScale ref', () => {
    const store = useResearchStore()
    store.setScale('macro')
    expect(store.currentScale.value).toBe('macro')

    store.setScale('micro')
    expect(store.currentScale.value).toBe('micro')
  })

  it('rejects unknown scales', () => {
    const store = useResearchStore()
    expect(() => store.setScale('nope')).toThrow(/scale/i)
  })

  it('is a singleton across calls', () => {
    const a = useResearchStore()
    const b = useResearchStore()
    a.setScale('micro')
    expect(b.currentScale.value).toBe('micro')
  })
})
