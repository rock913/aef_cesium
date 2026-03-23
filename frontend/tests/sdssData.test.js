import { describe, expect, it } from 'vitest'
import { normalizeSdssTriples } from '../src/utils/astronomy/sdssData.js'

describe('sdssData.normalizeSdssTriples', () => {
  it('parses 2D triples [[ra,dec,z],...]', () => {
    const input = [
      [10, 20, 0.1],
      [30, -40, 0.2],
    ]
    const out = normalizeSdssTriples(input)
    expect(out.count).toBe(2)
    expect(out.flat).toEqual([10, 20, 0.1, 30, -40, 0.2])
  })

  it('parses flat array [ra,dec,z,...]', () => {
    const input = [10, 20, 0.1, 30, -40, 0.2]
    const out = normalizeSdssTriples(input)
    expect(out.count).toBe(2)
    expect(out.flat).toEqual([10, 20, 0.1, 30, -40, 0.2])
  })

  it('ignores malformed rows in 2D format', () => {
    const input = [[10, 20], null, [30, -40, '0.2']]
    const out = normalizeSdssTriples(input)
    expect(out.count).toBe(1)
    expect(out.flat).toEqual([30, -40, 0.2])
  })
})
