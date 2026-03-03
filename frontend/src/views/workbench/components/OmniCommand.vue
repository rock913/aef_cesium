<template>
  <div class="omnibox" :class="{ open: open }" aria-label="Omni Command">
    <div class="omnibox-top">
      <span class="spark" aria-hidden="true">✦</span>
      <input
        ref="inputEl"
        class="omnibox-input"
        :value="modelValue"
        type="text"
        :placeholder="placeholder"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.enter.prevent="$emit('submit')"
        @keydown.esc.prevent="$emit('close')"
      />
      <div class="hint" aria-hidden="true">Cmd/Ctrl + K</div>
    </div>

    <div class="omnibox-context" v-if="contextLabel">
      <span class="k">已绑定上下文:</span>
      <span class="tag">@{{ contextLabel }}</span>
    </div>

    <div v-if="presets && presets.length" class="omnibox-presets" aria-label="Demo Presets">
      <div class="presets-title">⚡ 预置演示 (Demo Presets)</div>
      <ul class="presets-list">
        <li v-for="p in presets" :key="p.id" class="preset-row">
          <button class="preset-btn" type="button" @click="$emit('select-preset', p)">
            <span class="preset-label">{{ p.label }}</span>
            <span v-if="p.hint" class="preset-hint">{{ p.hint }}</span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入指令，例如：生成该区域的水文变化热力图…' },
  contextLabel: { type: String, default: '' },
  presets: { type: Array, default: () => [] },
})

defineEmits(['update:modelValue', 'submit', 'close', 'select-preset'])

const inputEl = ref(null)

watch(
  () => props.open,
  async (v) => {
    if (!v) return
    await nextTick()
    try {
      inputEl.value?.focus?.()
    } catch (_) {
      // ignore
    }
  }
)
</script>

<style scoped>
.omnibox {
  width: min(680px, calc(100vw - 24px));
  border-radius: 14px;
  overflow: hidden;
  background: rgba(15, 20, 35, 0.92);
  border: 1px solid rgba(0, 240, 255, 0.25);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.70);
}

.omnibox-top {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.spark {
  color: rgba(0, 240, 255, 0.9);
  font-size: 14px;
}

.omnibox-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: rgba(255, 255, 255, 0.95);
  font-size: 14px;
}

.hint {
  font-size: 11px;
  opacity: 0.60;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.omnibox-context {
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.35);
  font-size: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.k {
  opacity: 0.7;
}

.tag {
  color: rgba(157, 78, 221, 0.95);
  border: 1px solid rgba(157, 78, 221, 0.35);
  border-radius: 8px;
  padding: 2px 8px;
}

.omnibox-presets {
  padding: 10px;
  background: rgba(0, 0, 0, 0.18);
}

.presets-title {
  font-size: 11px;
  opacity: 0.72;
  letter-spacing: 0.06em;
  padding: 0 4px 8px;
}

.presets-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preset-btn {
  width: 100%;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.22);
  color: rgba(255, 255, 255, 0.92);
  cursor: pointer;
}

.preset-btn:hover {
  border-color: rgba(0, 240, 255, 0.35);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}

.preset-label {
  font-size: 13px;
}

.preset-hint {
  font-size: 10px;
  white-space: nowrap;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(0, 240, 255, 0.25);
  color: rgba(0, 240, 255, 0.9);
  background: rgba(0, 240, 255, 0.08);
}
</style>
