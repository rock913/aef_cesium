import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('Workbench wiring (best-practice)', () => {
  it('mounts WorkbenchApp on /workbench via dynamic import', () => {
    const s = read('../src/main.js')
    expect(s).toContain("path === '/workbench'")
    expect(s).toContain("import('./WorkbenchApp.vue')")
  })

  it('mounts Act2App on /act2 via dynamic import', () => {
    const s = read('../src/main.js')
    expect(s).toContain("path === '/act2'")
    expect(s).toContain("import('./Act2App.vue')")
  })

  it('lazy-loads monaco-editor only in workbench', () => {
    const s = read('../src/components/MonacoLazyEditor.vue')
    expect(s).toContain("import('../utils/monacoLoader.js')")
  })
})
