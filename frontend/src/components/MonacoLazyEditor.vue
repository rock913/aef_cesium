<template>
  <div class="monaco-shell" data-testid="monaco-shell">
    <div class="monaco-top">
      <div class="monaco-title">Editor</div>
      <div class="monaco-meta">
        <span v-if="loading" class="pill">Loading Monaco…</span>
        <span v-else-if="error" class="pill warn">Monaco unavailable</span>
        <span v-else class="pill ok">Monaco ready</span>
      </div>
    </div>

    <div v-if="error" class="fallback">
      <div class="fallback-hint">
        Monaco 没有加载成功（可能未安装依赖或被网络/构建环境限制）。已自动回退到轻量 textarea。
      </div>
      <textarea
        class="fallback-textarea"
        :value="modelValue"
        @input="onFallbackInput"
        spellcheck="false"
      />
    </div>

    <div v-else class="host" ref="hostEl" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'python' },
  theme: { type: String, default: 'vs-dark' },
  readOnly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const hostEl = ref(null)
const loading = ref(true)
const error = ref('')

let _editor = null
let _model = null
let _monaco = null

function onFallbackInput(e) {
  emit('update:modelValue', String(e?.target?.value ?? ''))
}

function _safeDispose(x) {
  try {
    x?.dispose?.()
  } catch (_) {
    // ignore
  }
}

onMounted(async () => {
  loading.value = true
  error.value = ''

  try {
    // Best practice: lazy-load Monaco only when the Workbench route is entered.
    // This keeps Landing's initial bundle small.
    const { loadMonaco } = await import('../utils/monacoLoader.js')
    _monaco = await loadMonaco()
    const editorApi = _monaco?.editor
    if (!editorApi || typeof editorApi.create !== 'function') throw new Error('monaco.editor.create is not available')

    const el = hostEl.value
    if (!el) {
      throw new Error('editor host element missing')
    }

    _model = editorApi.createModel(String(props.modelValue || ''), String(props.language || 'plaintext'))

    _editor = editorApi.create(el, {
      model: _model,
      theme: String(props.theme || 'vs-dark'),
      readOnly: !!props.readOnly,
      minimap: { enabled: false },
      fontSize: 13,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      automaticLayout: true,
      wordWrap: 'on',
    })

    _editor.onDidChangeModelContent(() => {
      try {
        const v = _editor?.getValue?.()
        emit('update:modelValue', String(v ?? ''))
      } catch (_) {
        // ignore
      }
    })
  } catch (e) {
    error.value = e?.message ? String(e.message) : 'failed to load monaco-editor'
  } finally {
    loading.value = false
  }
})

watch(
  () => props.modelValue,
  (v) => {
    if (!_editor) return
    try {
      const cur = _editor.getValue()
      const next = String(v ?? '')
      if (cur !== next) {
        _editor.setValue(next)
      }
    } catch (_) {
      // ignore
    }
  }
)

watch(
  () => props.language,
  (lang) => {
    if (!_model) return
    try {
      _monaco?.editor?.setModelLanguage?.(_model, String(lang || 'plaintext'))
    } catch (_) {
      // ignore
    }
  }
)

onBeforeUnmount(() => {
  _safeDispose(_editor)
  _safeDispose(_model)
  _editor = null
  _model = null
  _monaco = null
})
</script>

<style scoped>
.monaco-shell {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 280px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.monaco-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.monaco-title {
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.4px;
  opacity: 0.88;
}

.monaco-meta {
  display: flex;
  gap: 8px;
}

.pill {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(0, 0, 0, 0.25);
  opacity: 0.85;
}

.pill.ok {
  border-color: rgba(120, 255, 180, 0.28);
}

.pill.warn {
  border-color: rgba(255, 180, 120, 0.28);
}

.host {
  flex: 1;
  min-height: 260px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.fallback {
  flex: 1;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fallback-hint {
  font-size: 12px;
  opacity: 0.78;
}

.fallback-textarea {
  flex: 1;
  width: 100%;
  min-height: 260px;
  resize: none;
  padding: 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #eef2ff;
  outline: none;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.45;
}
</style>
