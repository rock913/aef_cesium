import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

function read(file) {
  const p = path.resolve(__dirname, file)
  return fs.readFileSync(p, 'utf-8')
}

describe('CopilotChatPanel v7.1 UI skeleton', () => {
  it('keeps a strict header/history/input-zone structure', () => {
    const s = read('../src/views/workbench/components/CopilotChatPanel.vue')
    expect(s).toContain('class="copilot-sidebar"')
    expect(s).toContain('class="header"')
    expect(s).toContain('class="chat-history"')
    expect(s).toContain('class="input-zone"')
    // v7.1+ input upgrade: capsule + command palette
    expect(s).toMatch(/capsule|command-palette|palette/i)
  })

  it('pins prompt chips directly above the textarea composer', () => {
    const s = read('../src/views/workbench/components/CopilotChatPanel.vue')

    // v7.1+ UX: remove the always-visible blue chips strip;
    // presets are accessed through the command palette list.
    expect(s).not.toContain('class="prompt-chips"')

    const inputZone = s.indexOf('class="input-zone"')
    const composer = s.indexOf('class="composer"')
    const textarea = s.indexOf('class="textarea"')
    const send = s.indexOf('class="send"')

    expect(inputZone).toBeGreaterThan(-1)
    expect(composer).toBeGreaterThan(-1)
    expect(textarea).toBeGreaterThan(-1)
    expect(send).toBeGreaterThan(-1)

    // Ensure order: input-zone -> composer (with textarea + send)
    expect(inputZone).toBeLessThan(composer)
    expect(composer).toBeLessThan(textarea)
    expect(textarea).toBeLessThan(send)
  })

  it('renders chat bubbles and a CoT accordion', () => {
    const s = read('../src/views/workbench/components/CopilotChatPanel.vue')
    expect(s).toContain('class="bubble user"')
    expect(s).toContain('class="bubble ai"')
    expect(s).toContain('aria-label="Tool Calling Accordion"')
    expect(s).toContain('<details')
    expect(s).toContain('<summary')
  })

  it('clears input after submit to avoid filtering presets', () => {
    const s = read('../src/views/workbench/components/CopilotChatPanel.vue')
    expect(s).toMatch(/function submit\(\)[\s\S]*text\.value\s*=\s*''/)
  })
})
