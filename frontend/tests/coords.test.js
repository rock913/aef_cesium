import { describe, it, expect } from 'vitest'
import { formatLatLon } from '../src/utils/coords.js'

describe('formatLatLon', () => {
  it('formats with default digits', () => {
    expect(formatLatLon(1.23456, 7.89012)).toBe('1.23456, 7.89012')
  })

  it('rounds to requested digits', () => {
    expect(formatLatLon(1.234567, 7.890129, 3)).toBe('1.235, 7.890')
  })

  it('returns dash when invalid', () => {
    expect(formatLatLon(undefined, 120.3)).toBe('—')
    expect(formatLatLon('abc', 'def')).toBe('—')
  })
})
