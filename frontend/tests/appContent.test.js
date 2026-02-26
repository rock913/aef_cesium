import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function readAppVue() {
  const p = path.resolve(__dirname, '../src/App.vue')
  return fs.readFileSync(p, 'utf-8')
}

function readIndexHtml() {
  const p = path.resolve(__dirname, '../index.html')
  return fs.readFileSync(p, 'utf-8')
}

describe('App.vue content guards', () => {
  it('does not contain leadership-view keyword', () => {
    const s = readAppVue()
    expect(s).not.toContain('领导视角')
  })

  it('removes OneEarth branding from UI strings', () => {
    const s = readAppVue()
    expect(s).not.toMatch(/\bONE EARTH\b/)
    expect(s).not.toMatch(/\bOneEarth\b/)
    expect(s).not.toMatch(/ONEEARTH\//)
    expect(s).toContain('ALPHA EARTH')
    expect(s).not.toMatch(/\bINTEL\b/)
    expect(s).toContain('DEMO')
  })

  it('updates document title branding', () => {
    const s = readIndexHtml()
    expect(s).toContain('Alpha Earth Demo')
    expect(s).not.toContain('ONE EARTH')
  })

  it('lobby cards keep compact (no narrative line)', () => {
    const s = readAppVue()
    expect(s).not.toContain('extractTagline(m.narrative)')
    expect(s).not.toContain('mission-card-desc')
  })

  it('lobby cards include operator formula tag', () => {
    const s = readAppVue()
    expect(s).toContain('m.formula')
    expect(s).toContain('tag tertiary formula')
  })
})
