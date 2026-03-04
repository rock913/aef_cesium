<template>
  <div class="copilot-sidebar" :class="{ collapsed }" aria-label="021 Copilot Chat">
    <!-- Top: Header -->
    <div class="header" aria-label="Copilot Header">
      <span class="brand">021 COPILOT</span>
      <button class="collapse" type="button" @click="collapsed = !collapsed">
        {{ collapsed ? '⇤ Expand' : '⇥ Collapse' }}
      </button>
    </div>

    <!-- Middle: Chat history -->
    <div v-if="!collapsed" class="chat-history" aria-label="Chat History">
      <div v-if="lastSubmitted" class="bubble user" aria-label="User Message">
        {{ lastSubmitted }}
      </div>

      <div v-if="events && events.length" class="cot" aria-label="Tool Calling Accordion">
        <details :open="cotOpen" @toggle="onToggleCot($event)">
          <summary class="cot-summary">
            <span v-if="busy">分析中…</span>
            <span v-else>✓ 分析完成</span>
            <span class="cot-time" v-if="elapsedLabel">({{ elapsedLabel }})</span>
          </summary>
          <div class="cot-body">
            <div v-for="(e, idx) in events" :key="idx" class="event">
              <div class="event-k">
                <span v-if="e.type === 'thought'">[思考]</span>
                <span v-else-if="e.type === 'tool_call'">[调用工具]</span>
                <span v-else-if="e.type === 'tool_result'">[工具结果]</span>
                <span v-else>[输出]</span>
                <span v-if="e.tool" class="event-tool">{{ e.tool }}</span>
              </div>
              <div v-if="e.text" class="event-v">{{ e.text }}</div>
              <pre v-else-if="e.args" class="event-pre">{{ formatJson(e.args) }}</pre>
              <pre v-else-if="e.result !== undefined" class="event-pre">{{ formatJson(e.result) }}</pre>
            </div>
          </div>
        </details>
      </div>

      <div v-if="aiFinalText" class="bubble ai" aria-label="AI Message">
        {{ aiFinalText }}
      </div>

      <div v-else-if="reportText" class="bubble ai" aria-label="AI Message">
        {{ reportText }}
      </div>

      <div v-else-if="agentText" class="bubble ai" aria-label="AI Message">
        {{ agentText }}
      </div>

      <div v-if="!lastSubmitted && !busy" class="hint" aria-label="Copilot Hint">
        Pick a preset chip or type a prompt to execute.
      </div>
    </div>

    <!-- Bottom: Input zone -->
    <div v-if="!collapsed" class="input-zone" aria-label="Input Zone">
      <div v-if="presets && presets.length" class="prompt-chips" aria-label="Prompt Gallery">
        <button
          v-for="p in presets"
          :key="p.id"
          class="chip"
          type="button"
          @click="applyPreset(p)"
        >
          {{ p.label }}
        </button>
      </div>

      <div class="composer" aria-label="Composer">
        <textarea
          class="textarea"
          v-model="text"
          rows="2"
          placeholder="输入自然语言指令…"
          @keydown="onKeydown"
        />
        <button class="send" type="button" :disabled="busy" @click="submit()" aria-label="Send">
          ↑
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  presets: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false },
  agentText: { type: String, default: '' },
  reportText: { type: String, default: '' },
  events: { type: Array, default: () => [] },
})

const emit = defineEmits(['submit', 'select-preset'])

const text = ref('')
const lastSubmitted = ref('')
const collapsed = ref(false)

const startedAtMs = ref(0)
const finishedAtMs = ref(0)
const cotOpen = ref(true)

const aiFinalText = computed(() => {
  const arr = Array.isArray(props.events) ? props.events : []
  const lastFinal = arr.slice().reverse().find((e) => String(e?.type || '') === 'final')
  const t = String(lastFinal?.text || '').trim()
  return t
})

const elapsedLabel = computed(() => {
  const start = Number(startedAtMs.value)
  if (!Number.isFinite(start) || start <= 0) return ''
  const end = Number((!props.busy && finishedAtMs.value) ? finishedAtMs.value : Date.now())
  const s = Math.max(0, (end - start) / 1000)
  if (!Number.isFinite(s)) return ''
  return `${s.toFixed(1)}s`
})

watch(
  () => props.busy,
  (v) => {
    if (v) return
    const arr = Array.isArray(props.events) ? props.events : []
    if (!arr.length) return
    finishedAtMs.value = Date.now()
    cotOpen.value = false
  }
)

function applyPreset(p) {
  emit('select-preset', p)
  try {
    const prompt = String(p?.prompt || '').trim()
    if (prompt) {
      text.value = prompt
      submit()
    }
  } catch (_) {
    // ignore
  }
}

function submit() {
  const v = String(text.value || '').trim()
  if (!v) return
  lastSubmitted.value = v
  startedAtMs.value = Date.now()
  finishedAtMs.value = 0
  cotOpen.value = true
  emit('submit', v)
}

function onKeydown(e) {
  const key = String(e?.key || '')
  if (key !== 'Enter') return
  if (e?.shiftKey) return
  e.preventDefault()
  submit()
}

function onToggleCot(ev) {
  try {
    cotOpen.value = !!ev?.target?.open
  } catch (_) {
    // ignore
  }
}

function formatJson(v) {
  try {
    return JSON.stringify(v, null, 2)
  } catch (_) {
    return String(v)
  }
}
</script>

<style scoped>

.copilot-sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.copilot-sidebar.collapsed {
  width: 64px;
}

.header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.22);
}

.brand {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.92);
  white-space: nowrap;
}

.collapse {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  font-size: 12px;
}

.collapse:hover {
  color: rgba(255, 255, 255, 0.88);
}

.chat-history {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bubble {
  max-width: 85%;
  border-radius: 12px;
  padding: 10px 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
}

.bubble.user {
  margin-left: auto;
  background: rgba(20, 110, 255, 0.40);
  border-color: rgba(20, 110, 255, 0.35);
  color: rgba(255, 255, 255, 0.95);
}

.bubble.ai {
  margin-right: auto;
  background: rgba(0, 0, 0, 0.22);
}

.hint {
  opacity: 0.75;
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.12);
}

.cot {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.18);
  padding: 8px 10px;
}

.cot-summary {
  cursor: pointer;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.68);
}

.cot-time {
  opacity: 0.7;
  margin-left: 6px;
}

.cot-body {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event {
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.20);
  padding: 8px 10px;
}

.event-k {
  font-size: 12px;
  opacity: 0.78;
  font-weight: 800;
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 6px;
}

.event-tool {
  color: rgba(0, 240, 255, 0.92);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-weight: 900;
}

.event-v {
  font-size: 12px;
  opacity: 0.92;
}

.event-pre {
  margin: 0;
  font-size: 11px;
  opacity: 0.88;
  white-space: pre-wrap;
}

.input-zone {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.prompt-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.prompt-chips::-webkit-scrollbar {
  height: 4px;
}

.prompt-chips::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.18);
  border-radius: 4px;
}

.chip {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(0, 240, 255, 0.92);
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

.chip:hover {
  border-color: rgba(0, 240, 255, 0.32);
  background: rgba(255, 255, 255, 0.08);
}

.composer {
  position: relative;
}

.textarea {
  width: 100%;
  resize: none;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(0, 0, 0, 0.35);
  color: rgba(255, 255, 255, 0.92);
  padding: 10px 38px 10px 10px;
  outline: none;
  font-size: 13px;
  line-height: 1.35;
}

.textarea:focus {
  border-color: rgba(0, 240, 255, 0.30);
  box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.08);
}

.send {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  border: 1px solid rgba(0, 240, 255, 0.25);
  background: rgba(0, 240, 255, 0.12);
  color: rgba(0, 240, 255, 0.92);
  cursor: pointer;
  font-weight: 900;
  line-height: 1;
}

.send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-body {
  font-size: 12px;
  line-height: 1.45;
}

.card-pre {
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.composer {
  display: flex;
  gap: 10px;
}

.input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.92);
  outline: none;
  font-size: 12px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(0, 240, 255, 0.18);
  border: 1px solid rgba(0, 240, 255, 0.35);
  color: #eaffff;
  cursor: pointer;
  font-size: 12px;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn.ghost {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.78);
}
</style>
