import { describe, it, expect } from 'vitest'
import { buildStubPlan, getOmniHelpText, parseOmniInput } from '../src/utils/omnibarCommands.js'

describe('Omni-Bar command palette (TDD gate)', () => {
  it('parses help', () => {
    expect(parseOmniInput('help').type).toBe('help')
    expect(parseOmniInput('/help').text).toContain('Commands:')
    expect(parseOmniInput('?').text).toContain('workbench')
    expect(getOmniHelpText()).toContain('act2')
  })

  it('parses navigation commands (robust casing/spacing)', () => {
    const a1 = parseOmniInput('   ACT2   ')
    expect(a1).toMatchObject({ type: 'navigate' })
    expect(a1.href).toContain('/act2')

    const a2 = parseOmniInput('/workbench')
    expect(a2).toEqual({ type: 'navigate', href: '/workbench', label: 'Open Workbench' })

    const a3 = parseOmniInput('demo')
    expect(a3).toEqual({ type: 'navigate', href: '/demo', label: 'Open Demo' })
  })

  it('supports act2 argument form', () => {
    const a = parseOmniInput('act2 yancheng')
    expect(a.type).toBe('navigate')
    expect(a.href).toContain('choreo=yancheng')
  })

  it('keeps free-form input as intent and produces stub plan', () => {
    const a = parseOmniInput('Build an agent to monitor Poyang Lake habitat')
    expect(a.type).toBe('intent')
    const plan = buildStubPlan(a.intent)
    expect(plan).toContain('Plan')
    expect(plan).toContain('Intent:')
  })
})
