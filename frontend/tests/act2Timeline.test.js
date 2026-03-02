import { describe, it, expect } from 'vitest'
import {
  ACT2_STEPS,
  normalizeAct2StepId,
  getAct2StepIndex,
  getNextAct2Step,
  getPrevAct2Step,
  resolveAct2Target,
  pickDominantAct2Entry,
} from '../src/utils/act2Timeline.js'

describe('Act2 timeline utils', () => {
  it('normalizes and orders step ids', () => {
    expect(ACT2_STEPS).toEqual(['space', 'earth', 'target', 'summary'])
    expect(normalizeAct2StepId(' SPACE ')).toBe('space')
    expect(normalizeAct2StepId('unknown')).toBe('')
    expect(getAct2StepIndex('earth')).toBe(1)
    expect(getNextAct2Step('earth')).toBe('target')
    expect(getPrevAct2Step('earth')).toBe('space')
  })

  it('resolves targets with defaults', () => {
    expect(resolveAct2Target('poyang')).toMatchObject({ lat: 29.12, lon: 116.23 })
    expect(resolveAct2Target('yancheng')).toMatchObject({ lat: 33.38, lon: 120.13 })
    expect(resolveAct2Target('yangtze')).toMatchObject({ lat: 31.23, lon: 121.47 })
    expect(resolveAct2Target('')).toMatchObject({ lat: 29.12, lon: 116.23 })
  })

  it('picks dominant intersection entry', () => {
    const a = { isIntersecting: true, intersectionRatio: 0.2, target: { dataset: { act2Step: 'space' } } }
    const b = { isIntersecting: true, intersectionRatio: 0.7, target: { dataset: { act2Step: 'earth' } } }
    const c = { isIntersecting: false, intersectionRatio: 0.99, target: { dataset: { act2Step: 'target' } } }
    expect(pickDominantAct2Entry([a, b, c])).toBe(b)
    expect(pickDominantAct2Entry([])).toBe(null)
  })
})
