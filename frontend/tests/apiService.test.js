import { describe, it, expect } from 'vitest'
import { apiService } from '../src/services/api.js'

describe('apiService', () => {
  it('exposes getSentinel2Layer()', () => {
    expect(typeof apiService.getSentinel2Layer).toBe('function')
  })
})
