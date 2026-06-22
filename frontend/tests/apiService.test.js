import { describe, it, expect } from 'vitest'
import { apiService } from '../src/services/api.js'

describe('apiService', () => {
  it('exposes getSentinel2Layer()', () => {
    expect(typeof apiService.getSentinel2Layer).toBe('function')
  })

  it('exposes v7 Copilot helpers', () => {
    expect(typeof apiService.listCopilotPrompts).toBe('function')
    expect(typeof apiService.executeCopilot).toBe('function')
  })
})
