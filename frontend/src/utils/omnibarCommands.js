import { buildAct2ChoreoHref } from './choreo.js'

function _norm(s) {
  return String(s || '')
    .trim()
    .replace(/\s+/g, ' ')
}

function _stripLeadingSlash(s) {
  return String(s || '').replace(/^\/+/, '')
}

export function getOmniHelpText() {
  return [
    'Commands:',
    '- act2 | earth | macro  → open Act 2 (poyang)',
    '- workbench | wb        → open /workbench',
    '- demo                  → open /demo',
    '- help                  → show this help',
    '',
    'Tip: You can also type a free-form intent. The MVP will preview a stub plan.',
  ].join('\n')
}

/**
 * Parse Omni-Bar input into an action.
 *
 * Output shapes:
 * - { type: 'help', text }
 * - { type: 'navigate', href, label }
 * - { type: 'intent', intent }
 */
export function parseOmniInput(input) {
  const raw = _norm(input)
  if (!raw) return { type: 'intent', intent: '' }

  const lowered = _stripLeadingSlash(raw).toLowerCase()

  // Allow an optional argument form: "act2 yancheng".
  const [cmd, arg] = lowered.split(' ')

  if (cmd === 'help' || cmd === '?') {
    return { type: 'help', text: getOmniHelpText() }
  }

  if (cmd === 'demo') {
    return { type: 'navigate', href: '/demo', label: 'Open Demo' }
  }

  if (cmd === 'workbench' || cmd === 'wb' || cmd === 'workspace') {
    return { type: 'navigate', href: '/workbench', label: 'Open Workbench' }
  }

  if (cmd === 'act2' || cmd === 'earth' || cmd === 'macro') {
    const choreo = String(arg || 'poyang').trim().toLowerCase() || 'poyang'
    return { type: 'navigate', href: buildAct2ChoreoHref(choreo), label: 'Open Act2' }
  }

  // Free-form intent
  return { type: 'intent', intent: raw }
}

export function buildStubPlan(intent) {
  const q = _norm(intent)
  if (!q) return ''

  return [
    `Intent: ${q}`,
    '',
    'Plan (stub):',
    '- 生成一个最小工作流：数据→分析→可视化',
    '- 推荐下一步：输入 “act2” 一键飞向鄱阳湖（/act2?choreo=poyang）',
  ].join('\n')
}
