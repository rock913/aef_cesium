<template>
  <div class="copilot" aria-label="021 Copilot Chat">
    <div class="head">
      <div class="title">021 COPILOT CHAT</div>
      <button class="btn ghost" type="button" @click="collapsed = !collapsed">
        {{ collapsed ? 'Expand' : 'Collapse' }}
      </button>
    </div>

    <div v-if="!collapsed" class="gallery" aria-label="Prompt Gallery">
      <div class="chips" role="list">
        <button
          v-for="p in presets"
          :key="p.id"
          class="chip"
          type="button"
          role="listitem"
          @click="applyPreset(p)"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div v-if="!collapsed" class="thread" aria-label="Chat Thread">
      <div class="card user" v-if="lastSubmitted">
        <div class="card-head">User</div>
        <div class="card-body">{{ lastSubmitted }}</div>
      </div>

      <div v-if="events && events.length" class="events" aria-label="Tool Calling Events">
        <div v-for="(e, idx) in events" :key="idx" class="card">
          <div class="card-head">
            <span v-if="e.type === 'thought'">思考</span>
            <span v-else-if="e.type === 'tool_call'">调用工具</span>
            <span v-else-if="e.type === 'tool_result'">工具结果</span>
            <span v-else>输出</span>
            <span v-if="e.tool" class="tool">{{ e.tool }}</span>
          </div>
          <div v-if="e.text" class="card-body">{{ e.text }}</div>
          <pre v-else-if="e.args" class="card-pre">{{ formatJson(e.args) }}</pre>
          <pre v-else-if="e.result !== undefined" class="card-pre">{{ formatJson(e.result) }}</pre>
        </div>
      </div>

      <div class="card" v-if="agentText">
        <div class="card-head">Plan / Flow</div>
        <pre class="card-pre">{{ agentText }}</pre>
      </div>

      <div class="card" v-if="reportText">
        <div class="card-head">Reports</div>
        <pre class="card-pre">{{ reportText }}</pre>
      </div>

      <div class="card hint" v-if="!lastSubmitted && !busy">
        <div class="card-head">Hint</div>
        <div class="card-body">Pick a preset chip or type a prompt to execute.</div>
      </div>
    </div>

    <div v-if="!collapsed" class="composer" aria-label="Composer">
      <input
        class="input"
        type="text"
        v-model="text"
        placeholder="Describe a task… (e.g. 扫描当前视窗进行零样本聚类)"
        @keydown.enter.prevent="submit()"
      />
      <button class="btn" type="button" :disabled="busy" @click="submit()">
        {{ busy ? 'Running…' : 'Run' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

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
  emit('submit', v)
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
.copilot {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.title {
  font-size: 11px;
  opacity: 0.78;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 900;
}

.gallery {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.18);
  padding: 10px;
}

.chips {
  display: flex;
  gap: 8px;
  overflow: auto;
  padding-bottom: 4px;
}

.chip {
  flex-shrink: 0;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0, 240, 255, 0.22);
  background: rgba(0, 240, 255, 0.08);
  color: rgba(0, 240, 255, 0.92);
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

.chip:hover {
  background: rgba(0, 240, 255, 0.12);
}

.thread {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.events {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
  padding: 10px;
}

.card.user {
  border-color: rgba(0, 240, 255, 0.22);
}

.card.hint {
  opacity: 0.82;
}

.card-head {
  font-size: 12px;
  opacity: 0.78;
  font-weight: 700;
  margin-bottom: 6px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.tool {
  opacity: 0.9;
  color: rgba(0, 240, 255, 0.92);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-weight: 800;
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
